# MediRush — Architecture

## Overview

MediRush is a smart ambulance dispatch application with two distinct layers:

1. **Dispatch Engine** — a Python CLI/simulation system that models city routing, hospital selection, and conflict resolution using graph algorithms.
2. **Web Application** — a full-stack Python (Flask) + vanilla JS app that lets end-users book ambulances, view history, and manage their medical profile.

---

## Repository Structure

```
smart_ambulance_dispatch/
│
├── src/                      # Python dispatch engine (core algorithms)
│   ├── graph.py              # City graph model with traffic simulation
│   ├── routing.py            # Dijkstra's algorithm + traffic change simulation
│   ├── hospital.py           # Hospital, Doctor, and HospitalSystem models
│   ├── dispatch.py           # Ambulance assignment + conflict resolution
│   └── ui.py                 # Interactive CLI and hospital ranker
│
├── run_app.py                # Interactive CLI entry point
├── main.py                   # Automated CLI demonstration
├── requirements.txt          # Python dependencies (all layers)
│
├── backend/                  # Flask REST API
│   ├── app.py                # Flask app + static file serving
│   ├── db.py                 # SQLite database layer (stdlib sqlite3)
│   ├── .env                  # Environment config (port, JWT secret, SMTP)
│   ├── middleware/
│   │   └── auth.py           # JWT verification decorator
│   └── routes/
│       ├── auth.py           # Register, OTP verify, complete-profile, login
│       ├── user.py           # User profile read/update
│       └── bookings.py       # Booking creation and history
│
├── frontend/                 # Vanilla HTML/CSS/JS web app
│   ├── shared.css            # Design system (tokens, cards, forms, buttons)
│   ├── index.html            # Auth page (login + 3-step registration)
│   └── app.html              # Dashboard (Book / History / Preferences)
│
└── medirush-v3.html          # Original standalone booking UI (source reference)
```

---

## Python Dispatch Engine

The core algorithmic layer. Runs independently of the web app and can be used via CLI or imported as a library.

### Data model

```
Graph
  ├── nodes          — city locations (A, B, C, D, E, …)
  ├── edges          — bidirectional roads with base travel times
  ├── traffic_density  — per-edge multiplier (0.5 = light, 2.5 = heavy)
  └── traffic_signals  — per-edge signal state (green/red, cycle timing)

HospitalSystem
  └── Hospital[]
        ├── location     — graph node where hospital sits
        ├── capacity     — total bed count
        ├── current_patients
        └── Doctor[]
              ├── specialty  (Emergency, Trauma, General, Orthopedic, …)
              └── available  — True when not treating a patient
```

### Routing (`src/routing.py`)

- **`dijkstra(graph, start)`** — standard Dijkstra over the `Graph` object using *dynamic* edge weights (`base_weight × traffic_density + signal_delay`).
- **`reconstruct_path(previous, start, target)`** — backtracks the predecessor map to produce a node list.
- **`simulate_traffic_changes(graph)`** — randomly mutates edge densities and advances signal phases; called every 5 seconds by a background thread in `run_app.py`.

### Dispatch (`src/dispatch.py`)

- **`assign_ambulance(graph, ambulances, patient_location, hospital_system, severity, target_hospital)`**
  1. Runs Dijkstra from every available ambulance node; picks the one closest to the patient.
  2. Ranks hospitals via `HospitalRanker` (travel time + processing delay).
  3. Calls `check_doctor_conflict` — verifies the target hospital has a doctor with the required specialty for the patient's severity level.
  4. If a conflict exists, calls `resolve_conflict` to find the next viable hospital.
  5. Calls `hospital.assign_patient_to_doctor` which marks the doctor as busy for an estimated treatment duration.
  6. Returns `(ambulance, total_time, route, hospital, doctor, conflict_info)`.

### Severity → specialty mapping

| Severity | Required specialties |
|----------|---------------------|
| CRITICAL | Emergency, Trauma |
| URGENT   | Emergency, General |
| MODERATE | General, Orthopedic |
| MILD     | General |

---

## Web Application

### Architecture

```
Browser
  │
  │  HTTP (same origin)
  ▼
Flask (backend/app.py, port 3001)
  ├── Static files  → frontend/
  ├── /api/auth/*   → routes/auth.py
  ├── /api/user/*   → routes/user.py
  └── /api/bookings/* → routes/bookings.py
              │
              ▼
         db.py (stdlib sqlite3)
              │
              ▼
       medirush.db  (SQLite file on disk)
```

The backend serves the frontend as static files, so the entire app runs on a single port with no CORS configuration needed in production.

### Database (`backend/db.py`)

SQLite via Python's built-in **sqlite3** module. WAL journal mode is enabled for better concurrent read performance.

**Tables:**

| Table | Purpose |
|-------|---------|
| `users` | Account credentials, name, phone, email verification flag |
| `user_medical` | Blood type, allergies, medications, conditions, emergency contact |
| `otps` | 6-digit codes with expiry and used flag |
| `bookings` | Full dispatch request record linked to a user |

### Authentication flow

```
Register (step 1)  →  POST /api/auth/register
                       Hash password (bcrypt), create unverified user, generate OTP,
                       send email (or print to console if SMTP not set)

OTP verify (step 2) → POST /api/auth/verify-otp
                       Validate code, mark user email_verified = 1

Medical profile (step 3) → POST /api/auth/complete-profile
                       Save name, phone, medical data → return JWT

Login              →  POST /api/auth/login
                       Verify password (bcrypt), return JWT (7-day expiry)
```

JWT is stored in `localStorage` on the client. All authenticated routes require an `Authorization: Bearer <token>` header, verified by `middleware/auth.py` (`@require_auth` decorator).

### API endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | — | Create account, send OTP |
| POST | `/api/auth/verify-otp` | — | Verify OTP |
| POST | `/api/auth/complete-profile` | — | Save medical info, get JWT |
| POST | `/api/auth/login` | — | Login, get JWT |
| GET  | `/api/user/profile` | JWT | Fetch profile + medical data |
| PUT  | `/api/user/profile` | JWT | Update profile + medical data |
| GET  | `/api/bookings` | JWT | List user's bookings (newest first) |
| POST | `/api/bookings` | JWT | Create a booking |

### Frontend (`frontend/`)

Two HTML pages driven by vanilla JavaScript — no build step, no framework.

**`index.html`** — Auth page with four in-page views:
- Login
- Register step 1 (email + password)
- Register step 2 (6-digit OTP entry)
- Register step 3 (medical profile form)

**`app.html`** — Dashboard with three sections switched via URL hash (`#book`, `#history`, `#preferences`):

| Section | Behaviour |
|---------|-----------|
| **Book** | The full booking flow (Who & Where → Emergency type → Confirm → Dispatched). Name and phone are pre-filled from the user's profile. Submission POSTs to `/api/bookings`. |
| **History** | GETs `/api/bookings` and renders a card list of past requests. |
| **Preferences** | GETs `/api/user/profile` and lets the user edit personal info and medical data. Saves via PUT `/api/user/profile`. |

**`shared.css`** — shared design system: CSS custom properties, card/form/button components, toast, and spinner. Both HTML files link to it and add page-specific styles inline.

### GPS tracking placeholder

The booking confirmation screen contains a clearly marked placeholder:

```html
<!-- ── GPS TRACKING PLACEHOLDER ────────────────────────────────────────
     TODO: Replace this card with a live map component (e.g. Leaflet.js
     or Google Maps) that subscribes to a WebSocket/SSE stream from the
     backend, showing the ambulance's real-time GPS position.
─────────────────────────────────────────────────────────────────────── -->
<div class="gps-placeholder"> … </div>
```

---

## Running the app

```bash
# Install dependencies
pip install -r requirements.txt

# Start server (initialises SQLite, then listens)
cd backend
python app.py
# → http://localhost:3001
```

OTPs print to console in development (no SMTP configured).

To enable email OTPs, set these in `backend/.env`:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASS=your_app_password
FROM_EMAIL=you@gmail.com
```

To run the Python dispatch CLI independently:
```bash
python3 run_app.py    # interactive UI
python3 main.py       # automated demo
```

---

## Extension points

| Feature | Where to add |
|---------|-------------|
| Live GPS tracking | Replace `gps-placeholder` div in `frontend/app.html` with a Leaflet/Google Maps component; add a WebSocket or SSE endpoint to `backend/app.py` |
| Push notifications | Add a `notifications` table; hook into booking creation in `routes/bookings.py` |
| Admin / dispatcher view | New frontend page + new Flask blueprint; reuse `middleware/auth.py` with a role field added to `users` |
| Real dispatch integration | Call the Python engine directly from `routes/bookings.py` (same process) or expose it as a dedicated `/api/dispatch` endpoint |
| PostgreSQL / MySQL | Replace `db.py` with `psycopg2` or `mysql-connector-python`; SQL is standard and routes need no changes |
