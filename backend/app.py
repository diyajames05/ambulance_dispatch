"""
app.py — MediRush Flask application.

Serves the frontend as static files and mounts all API blueprints.

Usage:
    python app.py
    # → http://localhost:3001
"""

import os
import sys

from dotenv import load_dotenv

# Load .env before anything else
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Allow imports from backend/ directory and project root
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, send_from_directory
from flask_cors import CORS

import db
from routes.auth import bp as auth_bp
from routes.bookings import bp as bookings_bp
from routes.user import bp as user_bp
from routes.dispatch import bp as dispatch_bp

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)


# ── API blueprints ────────────────────────────────────────────────────────────
app.register_blueprint(auth_bp,     url_prefix='/api/auth')
app.register_blueprint(user_bp,     url_prefix='/api/user')
app.register_blueprint(bookings_bp, url_prefix='/api/bookings')
app.register_blueprint(dispatch_bp, url_prefix='/api/map')


# ── Static frontend ───────────────────────────────────────────────────────────
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve frontend files; fall back to index.html for client-side routing."""
    file_path = os.path.join(FRONTEND_DIR, path)
    if path and os.path.isfile(file_path):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')


# ── Entry point ───────────────────────────────────────────────────────────────
def _load_dispatch_engine():
    """Load road graph and hospital system into app.config at startup."""
    from src.geo_graph import load_road_graph, build_hospital_system

    graph_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'road_graph.json')
    if not os.path.exists(graph_path):
        print('  WARNING: data/road_graph.json not found — run  python src/build_road_graph.py  first')
        return

    graph, hospitals_meta, ambulances_meta, bbox = load_road_graph(graph_path)
    hospital_system = build_hospital_system(hospitals_meta)

    app.config['ROAD_GRAPH'] = graph
    app.config['HOSPITAL_SYSTEM'] = hospital_system
    app.config['HOSPITALS_META'] = hospitals_meta
    app.config['AMBULANCES_META'] = ambulances_meta
    app.config['BBOX'] = bbox

    n_nodes = len(graph.graph)
    n_edges = sum(len(v) for v in graph.graph.values())
    print(f'  Dispatch engine loaded: {n_nodes} nodes, {n_edges} edges, '
          f'{len(hospitals_meta)} hospitals, {len(ambulances_meta)} ambulances')


if __name__ == '__main__':
    port = int(os.getenv('PORT', 3001))

    db.init()
    _load_dispatch_engine()

    print(f'\n  MediRush running at http://localhost:{port}\n')
    if not os.getenv('SMTP_HOST'):
        print('  SMTP not configured — OTPs will be printed to this console.\n')

    app.run(host='0.0.0.0', port=port, debug=False)
