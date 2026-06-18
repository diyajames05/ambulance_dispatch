"""
routes/auth.py — Authentication endpoints.

POST /api/auth/register          Create account, send OTP
POST /api/auth/verify-otp        Validate OTP, mark email verified
POST /api/auth/complete-profile  Save medical info, return JWT
POST /api/auth/login             Verify password, return JWT
"""

import os
import random
import re
import smtplib
import traceback
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import bcrypt
import jwt
from flask import Blueprint, jsonify, request

import db

bp = Blueprint('auth', __name__)

JWT_SECRET = os.getenv('JWT_SECRET', 'medirush_jwt_secret_change_in_production')
EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


# ── Email helper ──────────────────────────────────────────────────────────────

def _send_otp(email: str, otp: str):
    smtp_host = os.getenv('SMTP_HOST')
    smtp_user = os.getenv('SMTP_USER')
    smtp_pass = os.getenv('SMTP_PASS')

    if not (smtp_host and smtp_user and smtp_pass):
        print(f'\n  OTP for {email}: {otp}  (SMTP not configured — logged to console)\n')
        return

    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    from_email = os.getenv('FROM_EMAIL', smtp_user)

    html_body = f"""
    <div style="font-family:sans-serif;max-width:420px;margin:0 auto;padding:32px 24px">
      <h2 style="color:#d63031;margin:0 0 8px">MediRush</h2>
      <p style="color:#4a5568;margin:0 0 24px">Smart Ambulance Dispatch</p>
      <p>Your verification code is:</p>
      <div style="font-size:40px;font-weight:700;letter-spacing:10px;color:#d63031;
                  margin:20px 0;font-family:monospace">{otp}</div>
      <p style="color:#888;font-size:13px">
        This code expires in <strong>10 minutes</strong>. Do not share it with anyone.
      </p>
    </div>
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'MediRush — Your verification code'
    msg['From'] = from_email
    msg['To'] = email
    msg.attach(MIMEText(html_body, 'html'))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(from_email, email, msg.as_string())


# ── POST /api/auth/register ───────────────────────────────────────────────────

@bp.route('/register', methods=['POST'])
def register():
    try:
        body = request.get_json() or {}
        email = (body.get('email') or '').strip()
        password = body.get('password') or ''

        if not email or not password:
            return jsonify({'error': 'Email and password are required.'}), 400
        if not EMAIL_RE.match(email):
            return jsonify({'error': 'Please enter a valid email address.'}), 400
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters.'}), 400

        existing = db.query_one('SELECT id, email_verified FROM users WHERE email = ?', (email,))
        if existing and existing['email_verified']:
            return jsonify({'error': 'This email is already registered. Please sign in.'}), 400

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        if existing:
            db.execute('UPDATE users SET password_hash = ? WHERE email = ?', (password_hash, email))
        else:
            db.execute('INSERT INTO users (email, password_hash) VALUES (?, ?)', (email, password_hash))

        # Invalidate old OTPs and generate a new one
        db.execute('UPDATE otps SET used = 1 WHERE email = ? AND used = 0', (email,))
        otp = str(random.randint(100000, 999999))
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        db.execute('INSERT INTO otps (email, otp, expires_at) VALUES (?, ?, ?)', (email, otp, expires_at))

        _send_otp(email, otp)

        return jsonify({'message': 'Verification code sent to your email.'})
    except Exception:
        traceback.print_exc()
        return jsonify({'error': 'Server error. Please try again.'}), 500


# ── POST /api/auth/verify-otp ─────────────────────────────────────────────────

@bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    try:
        body = request.get_json() or {}
        email = (body.get('email') or '').strip()
        otp = (body.get('otp') or '').strip()

        if not email or not otp:
            return jsonify({'error': 'Email and OTP are required.'}), 400

        record = db.query_one(
            'SELECT * FROM otps WHERE email = ? AND used = 0 ORDER BY id DESC LIMIT 1',
            (email,)
        )

        if not record:
            return jsonify({'error': 'No pending code. Please register again.'}), 400

        expires = datetime.fromisoformat(record['expires_at'].replace('Z', '+00:00'))
        if expires < datetime.now(timezone.utc):
            return jsonify({'error': 'Code has expired. Please register again.'}), 400

        if record['otp'] != otp:
            return jsonify({'error': 'Incorrect code. Please try again.'}), 400

        db.execute('UPDATE otps SET used = 1 WHERE id = ?', (record['id'],))
        db.execute('UPDATE users SET email_verified = 1 WHERE email = ?', (email,))

        return jsonify({'message': 'Email verified successfully.'})
    except Exception:
        traceback.print_exc()
        return jsonify({'error': 'Server error. Please try again.'}), 500


# ── POST /api/auth/complete-profile ──────────────────────────────────────────

@bp.route('/complete-profile', methods=['POST'])
def complete_profile():
    try:
        body = request.get_json() or {}
        email = (body.get('email') or '').strip()
        full_name = (body.get('full_name') or '').strip()
        phone = body.get('phone') or None
        blood_type = body.get('blood_type') or None
        allergies = body.get('allergies') or None
        medications = body.get('medications') or None
        conditions = body.get('conditions') or None
        ec_name = body.get('emergency_contact_name') or None
        ec_phone = body.get('emergency_contact_phone') or None

        if not email or not full_name:
            return jsonify({'error': 'Email and full name are required.'}), 400

        user = db.query_one('SELECT id, email_verified FROM users WHERE email = ?', (email,))
        if not user:
            return jsonify({'error': 'User not found.'}), 400
        if not user['email_verified']:
            return jsonify({'error': 'Email not verified.'}), 400

        db.execute('UPDATE users SET full_name = ?, phone = ? WHERE id = ?',
                   (full_name, phone, user['id']))

        has_medical = db.query_one('SELECT user_id FROM user_medical WHERE user_id = ?', (user['id'],))
        if has_medical:
            db.execute(
                '''UPDATE user_medical
                   SET blood_type=?, allergies=?, medications=?, conditions=?,
                       emergency_contact_name=?, emergency_contact_phone=?
                   WHERE user_id=?''',
                (blood_type, allergies, medications, conditions, ec_name, ec_phone, user['id']),
            )
        else:
            db.execute(
                '''INSERT INTO user_medical
                     (user_id, blood_type, allergies, medications, conditions,
                      emergency_contact_name, emergency_contact_phone)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (user['id'], blood_type, allergies, medications, conditions, ec_name, ec_phone),
            )

        token = jwt.encode(
            {'id': user['id'], 'email': email, 'exp': datetime.now(timezone.utc) + timedelta(days=7)},
            JWT_SECRET, algorithm='HS256'
        )
        return jsonify({
            'token': token,
            'user': {'id': user['id'], 'email': email, 'full_name': full_name, 'phone': phone},
        })
    except Exception:
        traceback.print_exc()
        return jsonify({'error': 'Server error. Please try again.'}), 500


# ── POST /api/auth/login ──────────────────────────────────────────────────────

@bp.route('/login', methods=['POST'])
def login():
    try:
        body = request.get_json() or {}
        email = (body.get('email') or '').strip()
        password = body.get('password') or ''

        if not email or not password:
            return jsonify({'error': 'Email and password are required.'}), 400

        user = db.query_one('SELECT * FROM users WHERE email = ?', (email,))
        if not user:
            return jsonify({'error': 'Invalid email or password.'}), 401
        if not user['email_verified']:
            return jsonify({'error': 'Please verify your email before signing in.'}), 401

        if not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
            return jsonify({'error': 'Invalid email or password.'}), 401

        token = jwt.encode(
            {'id': user['id'], 'email': user['email'],
             'exp': datetime.now(timezone.utc) + timedelta(days=7)},
            JWT_SECRET, algorithm='HS256'
        )
        return jsonify({
            'token': token,
            'user': {
                'id': user['id'], 'email': user['email'],
                'full_name': user['full_name'], 'phone': user['phone'],
            },
        })
    except Exception:
        traceback.print_exc()
        return jsonify({'error': 'Server error. Please try again.'}), 500
