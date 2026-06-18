"""
Load pre-processed road graph JSON into the existing Graph class.
Provides snap-to-nearest-node utility for map clicks.
"""

import json
import math
from src.graph import Graph
from src.hospital import (
    Hospital, HospitalSystem, Doctor,
    DoctorSpecialty, PatientSeverity,
)


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def node_to_coords(node_id):
    """Parse 'lat,lon' node ID to (lat, lon) floats."""
    lat, lon = node_id.split(",")
    return float(lat), float(lon)


def snap_to_nearest_node(lat, lon, graph):
    """Find the closest graph node to (lat, lon). Returns (node_id, distance_km)."""
    best, best_dist = None, float("inf")
    for nid in graph.graph:
        nlat, nlon = node_to_coords(nid)
        d = haversine_km(lat, lon, nlat, nlon)
        if d < best_dist:
            best, best_dist = nid, d
    return best, best_dist


def load_road_graph(json_path):
    """
    Load pre-processed road graph into a Graph instance.

    Returns (graph, hospitals_meta, ambulances_meta, bbox)
    where hospitals_meta / ambulances_meta are dicts straight from the JSON.
    """
    with open(json_path) as f:
        data = json.load(f)

    g = Graph()
    for node in data["nodes"]:
        g.add_node(node)

    # add_edge also re-adds nodes and inits traffic_density/signals,
    # which is fine — values are just overwritten to defaults.
    for src, dst, weight in data["edges"]:
        g.graph.setdefault(src, []).append((dst, weight))
        edge_key = (src, dst)
        g.traffic_density[edge_key] = 1.0
        g.traffic_signals[edge_key] = None

    return g, data["hospitals"], data["ambulances"], data["bbox"]


def build_hospital_system(hospitals_meta):
    """
    Create a HospitalSystem with 3 hospitals and sample doctors.
    """
    hs = HospitalSystem()

    doctor_rosters = {
        "CMC": [
            Doctor("D1", "Lakshmi", DoctorSpecialty.EMERGENCY),
            Doctor("D2", "Rajan", DoctorSpecialty.TRAUMA),
            Doctor("D3", "Meena", DoctorSpecialty.CARDIOLOGY),
            Doctor("D4", "Kumar", DoctorSpecialty.GENERAL),
        ],
        "VIT": [
            Doctor("D5", "Priya", DoctorSpecialty.EMERGENCY),
            Doctor("D6", "Senthil", DoctorSpecialty.GENERAL),
            Doctor("D7", "Anita", DoctorSpecialty.ORTHOPEDIC),
        ],
        "KHC": [
            Doctor("D8", "Ramesh", DoctorSpecialty.EMERGENCY),
            Doctor("D9", "Divya", DoctorSpecialty.GENERAL),
            Doctor("D10", "Arun", DoctorSpecialty.TRAUMA),
        ],
    }

    capacities = {"CMC": 100, "VIT": 30, "KHC": 40}

    for hid, meta in hospitals_meta.items():
        h = Hospital(hid, meta["name"], meta["node"], capacities.get(hid, 50))
        for doc in doctor_rosters.get(hid, []):
            h.add_doctor(doc)
        hs.add_hospital(h)

    return hs
