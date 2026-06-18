import time
import random

class Graph:
    def __init__(self):
        self.graph = {}
        self.traffic_density = {}
        self.traffic_signals = {}

    def add_node(self, node):
        if node not in self.graph:
            self.graph[node] = []

    def add_edge(self, from_node, to_node, weight):
        if from_node not in self.graph:
            self.add_node(from_node)
        if to_node not in self.graph:
            self.add_node(to_node)

        edge_key = (from_node, to_node)
        self.graph[from_node].append((to_node, weight))
        self.traffic_density[edge_key] = 1.0
        self.traffic_signals[edge_key] = None

    def update_traffic(self, from_node, to_node, new_weight):
        """Dynamically update road weight (traffic simulation)"""
        for i, (neighbor, weight) in enumerate(self.graph[from_node]):
            if neighbor == to_node:
                self.graph[from_node][i] = (to_node, new_weight)
                break

    def set_traffic_density(self, from_node, to_node, density):
        """Set traffic density (1.0 = normal, >1.0 = congested, <1.0 = light)"""
        edge_key = (from_node, to_node)
        if edge_key in self.traffic_density:
            self.traffic_density[edge_key] = density

    def add_traffic_signal(self, from_node, to_node, signal_config):
        """Add traffic signal with timing configuration
        signal_config = {'cycle_time': 60, 'green_time': 30, 'current_phase': 'green', 'phase_start': time.time()}
        """
        edge_key = (from_node, to_node)
        if edge_key in self.traffic_signals:
            self.traffic_signals[edge_key] = signal_config

    def get_current_weight(self, from_node, to_node, base_weight):
        """Calculate current weight considering traffic and signals"""
        edge_key = (from_node, to_node)
        
        # Apply traffic density
        traffic_factor = self.traffic_density.get(edge_key, 1.0)
        current_weight = base_weight * traffic_factor
        
        # Apply traffic signal delay
        signal = self.traffic_signals.get(edge_key)
        if signal:
            current_time = time.time()
            elapsed = current_time - signal['phase_start']
            
            if signal['current_phase'] == 'red':
                remaining_red = signal['cycle_time'] - signal['green_time'] - elapsed
                if remaining_red > 0:
                    current_weight += remaining_red
            elif signal['current_phase'] == 'green':
                elapsed_green = elapsed
                if elapsed_green >= signal['green_time']:
                    current_weight += signal['cycle_time'] - signal['green_time']
        
        return current_weight

    def get_dynamic_neighbors(self, node):
        """Get neighbors with current dynamic weights"""
        neighbors = []
        for neighbor, base_weight in self.graph.get(node, []):
            current_weight = self.get_current_weight(node, neighbor, base_weight)
            neighbors.append((neighbor, current_weight))
        return neighbors

    def get_nodes(self):
        return list(self.graph.keys())

    def get_neighbors(self, node):
        return self.graph.get(node, [])
