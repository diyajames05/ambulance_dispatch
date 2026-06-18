# Smart Ambulance Dispatch System

A real-time dispatch and triage system designed to optimize patient outcomes by finding the fastest path to the most suitable hospital.

---

## Development Environment Setup

### Linux

**1. Install Python 3.10+**

```bash
sudo apt update
sudo apt install python3 python3-venv python3-full
```

Verify:
```bash
python3 --version
```

**2. Clone the repository**

```bash
git clone <repo-url>
cd smart_ambulance_dispatch
```

**3. Create and activate a virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate
```

Your prompt will change to show `(venv)`. To deactivate later: `deactivate`.

**4. Install dependencies**

```bash
pip install -r requirements.txt
```

**5. Configure environment variables**

```bash
cp backend/.env backend/.env  # already exists, just review it
```

Open `backend/.env` and set values as needed (see [Environment Variables](#environment-variables) below). For local development the defaults work without any changes — OTPs will print to the console.

**6. Start the server**

```bash
cd backend
python app.py
```

Open `http://localhost:3001` in your browser.

---

### Windows

**1. Install Python 3.10+**

Download the installer from [python.org](https://www.python.org/downloads/). During installation:
- Check "Add python.exe to PATH"
- Check "Use admin privileges when installing py.exe"

Verify in a new terminal (Command Prompt or PowerShell):
```cmd
python --version
```

**2. Clone the repository**

```cmd
git clone <repo-url>
cd smart_ambulance_dispatch
```

If you don't have Git, download it from [git-scm.com](https://git-scm.com).

**3. Create and activate a virtual environment**

Command Prompt:
```cmd
python -m venv venv
venv\Scripts\activate
```

PowerShell:
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

If PowerShell blocks the script, run this first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Your prompt will change to show `(venv)`. To deactivate later: `deactivate`.

**4. Install dependencies**

```cmd
pip install -r requirements.txt
```

**5. Configure environment variables**

Open `backend\.env` in any text editor and review the values. For local development the defaults work without any changes.

**6. Start the server**

```cmd
cd backend
python app.py
```

Open `http://localhost:3001` in your browser.

---

## Running the Dispatch CLI

The dispatch engine can be run independently of the web app.

Activate the virtual environment first (if not already active), then from the project root:

```bash
python3 run_app.py    # interactive dispatch UI
python3 main.py       # automated demo
```

---

## Project Structure

```
smart_ambulance_dispatch/
├── src/                  # Python dispatch engine (core algorithms)
│   ├── graph.py          # City graph with traffic simulation
│   ├── routing.py        # Dijkstra + traffic change simulation
│   ├── hospital.py       # Hospital, Doctor, HospitalSystem models
│   ├── dispatch.py       # Ambulance assignment + conflict resolution
│   └── ui.py             # Interactive CLI and hospital ranker
├── run_app.py            # Interactive CLI entry point
├── main.py               # Automated CLI demo
├── backend/              # Python (Flask) REST API
│   ├── app.py            # Flask app + static file serving
│   ├── db.py             # SQLite database layer
│   ├── .env              # Environment config (port, JWT secret, SMTP)
│   ├── middleware/
│   │   └── auth.py       # JWT verification decorator
│   └── routes/
│       ├── auth.py       # Register, OTP verify, complete-profile, login
│       ├── user.py       # User profile read/update
│       └── bookings.py   # Booking creation and history
├── frontend/             # Vanilla HTML/CSS/JS web app
│   ├── shared.css        # Design system
│   ├── index.html        # Auth page (login + 3-step registration)
│   └── app.html          # Dashboard (Book / History / Preferences)
└── requirements.txt      # Python dependencies
```

---

## Features

- **Real-time Hospital Ranking**: Ranks hospitals by travel time and processing delay.
- **Traffic-Aware Routing**: Dijkstra's algorithm with live traffic density and signal phases.
- **Intelligent Triage**: Injury Severity Score (ISS) matching to the right specialists.
- **Conflict Resolution**: Auto-redirects patients if the primary hospital is full or lacks required specialists.
- **System Monitoring**: Real-time bed capacity and doctor availability.

---

## Environment Variables

Located at `backend/.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3001` | Server port |
| `JWT_SECRET` | `medirush_jwt_secret_change_in_production` | JWT signing secret — change this in production |
| `SMTP_HOST` | — | SMTP server hostname. Leave blank to print OTPs to the console |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | — | SMTP username / email address |
| `SMTP_PASS` | — | SMTP password or app password |
| `FROM_EMAIL` | — | Sender address (defaults to `SMTP_USER` if not set) |

Example Gmail configuration:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASS=your_app_password
FROM_EMAIL=you@gmail.com
```

---

## Requirements

- Python 3.10+
- Dependencies: `pip install -r requirements.txt`
