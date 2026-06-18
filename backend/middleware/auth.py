"""
middleware/auth.py — JWT verification decorator.

Usage:
    from middleware.auth import require_auth
    ...
    @bp.route('/profile')
    @require_auth
    def profile():
        user = g.user   # {'id': ..., 'email': ...}
"""

import os
from functools import wraps

import jwt
from flask import g, jsonify, request

JWT_SECRET = os.getenv('JWT_SECRET', 'medirush_jwt_secret_change_in_production')


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        header = request.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            return jsonify({'error': 'No token provided'}), 401
        token = header[7:]
        try:
            g.user = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid or expired token'}), 401
        return f(*args, **kwargs)
    return decorated
