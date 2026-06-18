import heapq
import time

def dijkstra(graph_obj, start):
    graph = graph_obj.graph
    distances = {node: float('inf') for node in graph}
    previous = {node: None for node in graph}

    distances[start] = 0
    priority_queue = [(0, start)]

    while priority_queue:
        current_distance, current_node = heapq.heappop(priority_queue)

        if current_distance > distances[current_node]:
            continue

        # Use dynamic neighbors with current traffic and signal weights
        for neighbor, weight in graph_obj.get_dynamic_neighbors(current_node):
            distance = current_distance + weight

            if distance < distances[neighbor]:
                distances[neighbor] = distance
                previous[neighbor] = current_node
                heapq.heappush(priority_queue, (distance, neighbor))

    return distances, previous


def reconstruct_path(previous, start, target):
    path = []
    current = target

    while current is not None:
        path.append(current)
        current = previous[current]

    path.reverse()

    if path[0] == start:
        return path
    return []


def simulate_traffic_changes(graph_obj):
    """Simulate random traffic changes for demonstration"""
    import random
    current_time = time.time()
    
    for edge_key in graph_obj.traffic_density:
        if random.random() < 0.1:  # 10% chance of traffic change
            # Random traffic density between 0.5 (light) and 2.5 (heavy)
            new_density = random.uniform(0.5, 2.5)
            graph_obj.traffic_density[edge_key] = new_density
    
    # Update traffic signal phases
    for edge_key, signal in graph_obj.traffic_signals.items():
        if signal and signal is not None:
            elapsed = current_time - signal['phase_start']
            
            if signal['current_phase'] == 'green' and elapsed >= signal['green_time']:
                signal['current_phase'] = 'red'
                signal['phase_start'] = current_time
            elif signal['current_phase'] == 'red' and elapsed >= (signal['cycle_time'] - signal['green_time']):
                signal['current_phase'] = 'green'
                signal['phase_start'] = current_time
