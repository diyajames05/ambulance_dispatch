"""
/api/map/* endpoints — map config, road data, and ambulance dispatch.
"""

import os
import json
from flask import Blueprint, request, jsonify, send_file, current_app

bp = Blueprint('dispatch', __name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')


@bp.route('/config', methods=['GET'])
def map_config():
    """Return hospital locations, ambulance positions, bbox, and map centre."""
    hospitals = current_app.config['HOSPITALS_META']
    ambulances = current_app.config['AMBULANCES_META']
    bbox = current_app.config['BBOX']

    # Map centre = average of hospital positions
    lats = [h['lat'] for h in hospitals.values()]
    lons = [h['lon'] for h in hospitals.values()]
    centre = [sum(lats) / len(lats), sum(lons) / len(lons)]

    return jsonify({
        'hospitals': hospitals,
        'ambulances': ambulances,
        'bbox': bbox,
        'centre': centre,
    })


@bp.route('/roads', methods=['GET'])
def roads_geojson():
    """Serve the filtered roads GeoJSON for Leaflet rendering."""
    path = os.path.join(DATA_DIR, 'roads_display.geojson')
    return send_file(path, mimetype='application/geo+json')


@bp.route('/dispatch', methods=['POST'])
def dispatch():
    """
    Accept a map click + severity, run dispatch, return route + ETA.

    Request JSON:
        { "lat": float, "lon": float, "severity": "CRITICAL"|"URGENT"|"MODERATE"|"MILD" }

    Response JSON:
        { ambulance, patient_node, hospital, route_to_patient, route_to_hospital,
          eta_to_patient, eta_total, doctor, conflict_info }
    """
    from src.geo_graph import snap_to_nearest_node, node_to_coords
    from src.routing import dijkstra, reconstruct_path
    from src.dispatch import assign_ambulance
    from src.hospital import PatientSeverity

    data = request.get_json(force=True)
    lat = data.get('lat')
    lon = data.get('lon')
    sev_str = data.get('severity', 'MODERATE')

    if lat is None or lon is None:
        return jsonify({'error': 'lat and lon are required'}), 400

    # Validate within bbox
    bbox = current_app.config['BBOX']
    if not (bbox['min_lat'] <= lat <= bbox['max_lat'] and
            bbox['min_lon'] <= lon <= bbox['max_lon']):
        return jsonify({'error': 'Location is outside the service area'}), 400

    severity_map = {
        'CRITICAL': PatientSeverity.CRITICAL,
        'URGENT': PatientSeverity.URGENT,
        'MODERATE': PatientSeverity.MODERATE,
        'MILD': PatientSeverity.MILD,
    }
    severity = severity_map.get(sev_str, PatientSeverity.MODERATE)

    graph = current_app.config['ROAD_GRAPH']
    hospital_system = current_app.config['HOSPITAL_SYSTEM']
    ambulances_meta = current_app.config['AMBULANCES_META']

    # Snap click to nearest node
    patient_node, snap_dist = snap_to_nearest_node(lat, lon, graph)
    if patient_node is None:
        return jsonify({'error': 'Could not snap to road network'}), 400

    # Ambulance node list
    amb_nodes = [a['node'] for a in ambulances_meta.values()]
    amb_ids = list(ambulances_meta.keys())

    # Run dispatch
    best_amb_node, total_time, path_to_patient, hospital, doctor, conflict_info = \
        assign_ambulance(graph, amb_nodes, patient_node, hospital_system, severity)

    if best_amb_node is None:
        return jsonify({'error': 'No ambulance available'}), 500

    # Identify which ambulance
    amb_idx = amb_nodes.index(best_amb_node)
    amb_id = amb_ids[amb_idx]
    amb_meta = ambulances_meta[amb_id]

    # Convert path nodes → coordinate arrays for map drawing
    def path_to_coords(path):
        return [[float(x) for x in n.split(",")] for n in path]

    route_to_patient = path_to_coords(path_to_patient)

    # Compute route from patient to hospital
    route_to_hospital = []
    hospital_info = None
    eta_to_hospital = 0

    if hospital:
        distances, previous = dijkstra(graph, patient_node)
        hosp_time = distances.get(hospital.location, float('inf'))
        path_p2h = reconstruct_path(previous, patient_node, hospital.location)
        route_to_hospital = path_to_coords(path_p2h)
        eta_to_hospital = round(hosp_time, 1)

        hospital_info = {
            'id': hospital.id,
            'name': hospital.name,
            'lat': node_to_coords(hospital.location)[0],
            'lon': node_to_coords(hospital.location)[1],
            'beds_available': hospital.get_bed_availability(),
        }

    # ETA: ambulance to patient
    eta_to_patient = round(total_time - eta_to_hospital, 1) if hospital else round(total_time, 1)

    patient_lat, patient_lon = node_to_coords(patient_node)

    return jsonify({
        'ambulance': {
            'id': amb_id,
            'lat': amb_meta['lat'],
            'lon': amb_meta['lon'],
        },
        'patient_node': {
            'lat': patient_lat,
            'lon': patient_lon,
            'snap_distance_m': round(snap_dist * 1000, 0),
        },
        'hospital': hospital_info,
        'route_to_patient': route_to_patient,
        'route_to_hospital': route_to_hospital,
        'eta_to_patient': eta_to_patient,
        'eta_total': round(total_time, 1),
        'doctor': str(doctor) if doctor else None,
        'conflict_info': conflict_info,
    })
