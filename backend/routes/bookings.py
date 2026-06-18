"""
routes/bookings.py — Booking endpoints (auth required).

GET  /api/bookings   List user's bookings (newest first)
POST /api/bookings   Create a new booking
"""

import time
import traceback

import db
from flask import Blueprint, g, jsonify, request
from middleware.auth import require_auth

bp = Blueprint('bookings', __name__)


# ── GET /api/bookings ─────────────────────────────────────────────────────────

@bp.route('/', methods=['GET'])
@require_auth
def list_bookings():
    try:
        bookings = db.query_all(
            'SELECT * FROM bookings WHERE user_id = ? ORDER BY created_at DESC',
            (g.user['id'],)
        )
        return jsonify(bookings)
    except Exception:
        traceback.print_exc()
        return jsonify({'error': 'Server error.'}), 500


# ── POST /api/bookings ────────────────────────────────────────────────────────

@bp.route('/', methods=['POST'])
@require_auth
def create_booking():
    try:
        body = request.get_json() or {}
        location = body.get('location')
        emergency_type = body.get('emergency_type')
        severity_level = body.get('severity_level')

        if not location or not emergency_type or not severity_level:
            return jsonify({'error': 'location, emergency_type, and severity_level are required.'}), 400

        request_id = 'MR-' + str(int(time.time() * 1000))[-6:]

        db.execute(
            '''INSERT INTO bookings
                 (user_id, request_id, patient_name, patient_phone, location,
                  emergency_type, ambulance_type, severity_level, severity_word,
                  description, eta_minutes, unit_assigned)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                g.user['id'], request_id,
                body.get('patient_name'), body.get('patient_phone'), location,
                emergency_type, body.get('ambulance_type'),
                severity_level, body.get('severity_word'),
                body.get('description'), body.get('eta_minutes'), body.get('unit_assigned'),
            )
        )

        return jsonify({'request_id': request_id}), 201
    except Exception:
        traceback.print_exc()
        return jsonify({'error': 'Server error.'}), 500
