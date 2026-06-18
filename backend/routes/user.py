"""
routes/user.py — User profile endpoints (auth required).

GET /api/user/profile   Fetch profile + medical data
PUT /api/user/profile   Update profile + medical data
"""

import traceback

import db
from flask import Blueprint, g, jsonify, request
from middleware.auth import require_auth

bp = Blueprint('user', __name__)


# ── GET /api/user/profile ─────────────────────────────────────────────────────

@bp.route('/profile', methods=['GET'])
@require_auth
def get_profile():
    try:
        user = db.query_one(
            'SELECT id, email, full_name, phone, created_at FROM users WHERE id = ?',
            (g.user['id'],)
        )
        if not user:
            return jsonify({'error': 'User not found.'}), 404

        medical = db.query_one('SELECT * FROM user_medical WHERE user_id = ?', (g.user['id'],))
        return jsonify({**user, 'medical': medical or {}})
    except Exception:
        traceback.print_exc()
        return jsonify({'error': 'Server error.'}), 500


# ── PUT /api/user/profile ─────────────────────────────────────────────────────

@bp.route('/profile', methods=['PUT'])
@require_auth
def update_profile():
    try:
        body = request.get_json() or {}
        full_name = body.get('full_name') or None
        phone = body.get('phone') or None
        blood_type = body.get('blood_type') or None
        allergies = body.get('allergies') or None
        medications = body.get('medications') or None
        conditions = body.get('conditions') or None
        ec_name = body.get('emergency_contact_name') or None
        ec_phone = body.get('emergency_contact_phone') or None

        db.execute('UPDATE users SET full_name = ?, phone = ? WHERE id = ?',
                   (full_name, phone, g.user['id']))

        has_medical = db.query_one('SELECT user_id FROM user_medical WHERE user_id = ?', (g.user['id'],))
        if has_medical:
            db.execute(
                '''UPDATE user_medical
                   SET blood_type=?, allergies=?, medications=?, conditions=?,
                       emergency_contact_name=?, emergency_contact_phone=?
                   WHERE user_id=?''',
                (blood_type, allergies, medications, conditions, ec_name, ec_phone, g.user['id']),
            )
        else:
            db.execute(
                '''INSERT INTO user_medical
                     (user_id, blood_type, allergies, medications, conditions,
                      emergency_contact_name, emergency_contact_phone)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (g.user['id'], blood_type, allergies, medications, conditions, ec_name, ec_phone),
            )

        return jsonify({'message': 'Profile updated.'})
    except Exception:
        traceback.print_exc()
        return jsonify({'error': 'Server error.'}), 500
