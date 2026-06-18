"""
Pre-processing script: parse OSM GeoJSON extract → road graph JSON + display GeoJSON.

Run once:  python src/build_road_graph.py

Outputs:
  data/road_graph.json       – compact graph for backend dispatch
  data/roads_display.geojson – filtered roads for Leaflet rendering
"""

import json
import math
import os
from collections import defaultdict, deque

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GEOJSON_PATH = os.path.join(
    os.path.dirname(__file__), "..",
    "planet_78.661,12.682_79.596,13.309.osm.geojson",
)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

BBOX = {
    "min_lat": 12.90, "max_lat": 12.99,
    "min_lon": 79.10, "max_lon": 79.18,
}

DRIVEABLE_TYPES = {
    "trunk", "trunk_link",
    "primary", "primary_link",
    "secondary", "secondary_link",
    "tertiary", "tertiary_link",
    "residential", "unclassified",
    "living_street", "road", "service",
}

# Assumed average speeds (km/h) by highway type
SPEED_MAP = {
    "trunk": 60, "trunk_link": 40,
    "primary": 50, "primary_link": 35,
    "secondary": 40, "secondary_link": 30,
    "tertiary": 35, "tertiary_link": 25,
    "residential": 25, "unclassified": 25,
    "living_street": 15, "road": 25, "service": 15,
}

ROUND_DIGITS = 5  # ~1.1 m precision

HOSPITALS = {
    "CMC": {"name": "CMC Vellore", "lat": 12.92435, "lon": 79.13512},
    "VIT": {"name": "VIT Health Centre", "lat": 12.96846, "lon": 79.15595},
    "KHC": {"name": "Karigiri Health Centre", "lat": 12.96951, "lon": 79.14886},
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points in kilometres."""
    R = 6371.0
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def make_node_id(lat, lon):
    return f"{round(lat, ROUND_DIGITS)},{round(lon, ROUND_DIGITS)}"


def coord_in_bbox(lon, lat):
    return (BBOX["min_lat"] <= lat <= BBOX["max_lat"] and
            BBOX["min_lon"] <= lon <= BBOX["max_lon"])


def snap_to_nearest(lat, lon, nodes):
    """Find the graph node closest to (lat, lon)."""
    best, best_dist = None, float("inf")
    for nid in nodes:
        nlat, nlon = (float(x) for x in nid.split(","))
        d = haversine_km(lat, lon, nlat, nlon)
        if d < best_dist:
            best, best_dist = nid, d
    return best, best_dist


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build():
    print("Loading GeoJSON …")
    with open(GEOJSON_PATH) as f:
        data = json.load(f)

    adj = defaultdict(list)          # node_id → [(neighbour_id, weight)]
    all_nodes = set()
    display_features = []            # for roads_display.geojson
    edge_count = 0

    print("Filtering roads …")
    for feat in data["features"]:
        geom = feat.get("geometry")
        if not geom or geom["type"] != "LineString":
            continue
        props = feat.get("properties", {})
        hw = props.get("highway", "")
        if hw not in DRIVEABLE_TYPES:
            continue

        coords = geom["coordinates"]  # [lon, lat, …]
        # check if any coordinate falls in bbox
        if not any(coord_in_bbox(c[0], c[1]) for c in coords):
            continue

        speed = SPEED_MAP.get(hw, 25)
        oneway = props.get("oneway") == "yes"

        # Build edges for consecutive coordinate pairs
        for i in range(len(coords) - 1):
            lon1, lat1 = coords[i][0], coords[i][1]
            lon2, lat2 = coords[i + 1][0], coords[i + 1][1]

            # Only keep edges where at least one endpoint is in bbox
            if not (coord_in_bbox(lon1, lat1) or coord_in_bbox(lon2, lat2)):
                continue

            nid_a = make_node_id(lat1, lon1)
            nid_b = make_node_id(lat2, lon2)
            if nid_a == nid_b:
                continue

            dist_km = haversine_km(lat1, lon1, lat2, lon2)
            weight = (dist_km / speed) * 60  # minutes

            adj[nid_a].append((nid_b, round(weight, 6)))
            all_nodes.add(nid_a)
            all_nodes.add(nid_b)
            edge_count += 1

            if not oneway:
                adj[nid_b].append((nid_a, round(weight, 6)))
                edge_count += 1

        # Keep feature for display (strip heavy properties)
        display_features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": {"highway": hw, "name": props.get("name", "")},
        })

    print(f"  Raw: {len(all_nodes)} nodes, {edge_count} edges, {len(display_features)} display roads")

    # ------------------------------------------------------------------
    # Connected-component check (BFS from first hospital)
    # ------------------------------------------------------------------
    print("Finding largest connected component …")
    first_hospital_node, _ = snap_to_nearest(
        HOSPITALS["CMC"]["lat"], HOSPITALS["CMC"]["lon"], all_nodes
    )

    visited = set()
    queue = deque([first_hospital_node])
    visited.add(first_hospital_node)
    while queue:
        node = queue.popleft()
        for nbr, _ in adj.get(node, []):
            if nbr not in visited:
                visited.add(nbr)
                queue.append(nbr)

    # Also do reverse BFS to handle directed edges
    rev_adj = defaultdict(list)
    for n, neighbors in adj.items():
        for nbr, w in neighbors:
            rev_adj[nbr].append((n, w))
    queue = deque([first_hospital_node])
    rev_visited = {first_hospital_node}
    while queue:
        node = queue.popleft()
        for nbr, _ in rev_adj.get(node, []):
            if nbr not in rev_visited:
                rev_visited.add(nbr)
                queue.append(nbr)

    reachable = visited | rev_visited
    pruned = len(all_nodes) - len(reachable)
    all_nodes = all_nodes & reachable
    # Prune adj
    for n in list(adj.keys()):
        if n not in reachable:
            del adj[n]
        else:
            adj[n] = [(nb, w) for nb, w in adj[n] if nb in reachable]

    print(f"  Reachable: {len(all_nodes)} nodes (pruned {pruned})")

    # ------------------------------------------------------------------
    # Snap hospitals
    # ------------------------------------------------------------------
    print("Snapping hospitals …")
    hospitals_out = {}
    for hid, h in HOSPITALS.items():
        node, dist = snap_to_nearest(h["lat"], h["lon"], all_nodes)
        nlat, nlon = (float(x) for x in node.split(","))
        hospitals_out[hid] = {
            "name": h["name"],
            "node": node,
            "lat": nlat,
            "lon": nlon,
        }
        print(f"  {h['name']} → {node} (snap distance: {dist*1000:.0f} m)")

    # ------------------------------------------------------------------
    # Place ambulances at strategic nodes on major roads
    # ------------------------------------------------------------------
    print("Placing ambulances …")
    # Place near: south of CMC, between CMC and VIT, east of VIT
    amb_targets = [
        (12.915, 79.135),  # south of CMC
        (12.950, 79.145),  # midpoint between hospitals
        (12.965, 79.160),  # east of VIT
    ]
    ambulances_out = {}
    for i, (alat, alon) in enumerate(amb_targets, 1):
        node, dist = snap_to_nearest(alat, alon, all_nodes)
        nlat, nlon = (float(x) for x in node.split(","))
        ambulances_out[f"AMB-{i}"] = {
            "node": node,
            "lat": nlat,
            "lon": nlon,
        }
        print(f"  AMB-{i} → {node} (snap distance: {dist*1000:.0f} m)")

    # ------------------------------------------------------------------
    # Serialize edges list
    # ------------------------------------------------------------------
    edges_list = []
    for src, neighbors in adj.items():
        for dst, w in neighbors:
            edges_list.append([src, dst, w])

    graph_data = {
        "nodes": sorted(all_nodes),
        "edges": edges_list,
        "hospitals": hospitals_out,
        "ambulances": ambulances_out,
        "bbox": BBOX,
    }

    # ------------------------------------------------------------------
    # Write outputs
    # ------------------------------------------------------------------
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    graph_path = os.path.join(OUTPUT_DIR, "road_graph.json")
    with open(graph_path, "w") as f:
        json.dump(graph_data, f)
    sz = os.path.getsize(graph_path) / 1024
    print(f"Wrote {graph_path} ({sz:.0f} KB)")

    display_path = os.path.join(OUTPUT_DIR, "roads_display.geojson")
    with open(display_path, "w") as f:
        json.dump({"type": "FeatureCollection", "features": display_features}, f)
    sz = os.path.getsize(display_path) / 1024
    print(f"Wrote {display_path} ({sz:.0f} KB)")

    print(f"\nDone. {len(all_nodes)} nodes, {len(edges_list)} edges.")


if __name__ == "__main__":
    build()
