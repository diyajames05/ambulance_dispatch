from src.graph import Graph
from src.dispatch import assign_ambulance, prioritize_patients
from src.routing import simulate_traffic_changes
from src.hospital import Hospital, Doctor, DoctorSpecialty, PatientSeverity, HospitalSystem
import time


def build_hospital_system():
    hospital_system = HospitalSystem()
    
    # Create hospitals at different locations
    hospital1 = Hospital("H1", "City General Hospital", "C", capacity=50)
    hospital2 = Hospital("H2", "St. Mary's Medical Center", "E", capacity=30)
    hospital3 = Hospital("H3", "Emergency Care Unit", "A", capacity=20)
    
    # Add doctors to Hospital 1
    hospital1.add_doctor(Doctor("D1", "Dr. Smith", DoctorSpecialty.EMERGENCY))
    hospital1.add_doctor(Doctor("D2", "Dr. Johnson", DoctorSpecialty.TRAUMA))
    hospital1.add_doctor(Doctor("D3", "Dr. Williams", DoctorSpecialty.GENERAL))
    
    # Add doctors to Hospital 2
    hospital2.add_doctor(Doctor("D4", "Dr. Brown", DoctorSpecialty.EMERGENCY))
    hospital2.add_doctor(Doctor("D5", "Dr. Davis", DoctorSpecialty.GENERAL))
    
    # Add doctors to Hospital 3
    hospital3.add_doctor(Doctor("D6", "Dr. Miller", DoctorSpecialty.EMERGENCY))
    hospital3.add_doctor(Doctor("D7", "Dr. Wilson", DoctorSpecialty.ORTHOPEDIC))
    
    hospital_system.add_hospital(hospital1)
    hospital_system.add_hospital(hospital2)
    hospital_system.add_hospital(hospital3)
    
    return hospital_system


def build_city():
    city = Graph()

    nodes = ["A", "B", "C", "D", "E"]
    for node in nodes:
        city.add_node(node)

    # Add roads with base travel times
    city.add_edge("A", "B", 4)
    city.add_edge("B", "C", 3)
    city.add_edge("A", "D", 2)
    city.add_edge("D", "C", 5)
    city.add_edge("C", "E", 6)
    city.add_edge("B", "E", 10)

    # Set traffic densities (1.0 = normal, >1.0 = congested, <1.0 = light)
    city.set_traffic_density("A", "B", 1.5)  # Moderate traffic
    city.set_traffic_density("B", "C", 2.0)  # Heavy traffic
    city.set_traffic_density("A", "D", 0.8)  # Light traffic
    city.set_traffic_density("D", "C", 1.2)  # Slight congestion
    city.set_traffic_density("C", "E", 1.8)  # Heavy traffic
    city.set_traffic_density("B", "E", 1.0)  # Normal traffic

    # Add traffic signals at major intersections
    current_time = time.time()
    city.add_traffic_signal("A", "B", {
        'cycle_time': 60,      # 60 second total cycle
        'green_time': 30,      # 30 seconds green
        'current_phase': 'green',
        'phase_start': current_time
    })
    
    city.add_traffic_signal("C", "E", {
        'cycle_time': 90,      # 90 second total cycle
        'green_time': 45,      # 45 seconds green
        'current_phase': 'red',
        'phase_start': current_time
    })

    return city


def main():
    print("=== Smart Ambulance Dispatch System with Hospital Priority ===")
    print()

    city = build_city()
    hospital_system = build_hospital_system()
    ambulances = ["A", "B"]
    
    print(hospital_system.get_system_status())
    print()

    # Create multiple patients with different severities
    patients = [
        ("E", PatientSeverity.CRITICAL),
        ("B", PatientSeverity.URGENT),
        ("D", PatientSeverity.MODERATE),
        ("A", PatientSeverity.MILD)
    ]
    
    # Prioritize patients by severity
    prioritized_patients = prioritize_patients(patients)
    
    print("=== Patient Dispatch Queue (Prioritized by Severity) ===")
    for location, severity in prioritized_patients:
        print(f"Dispatching to {location} - Severity: {severity.name}")
        
        ambulance, time_taken, path, hospital, doctor, conflict_info = assign_ambulance(
            city, ambulances, location, hospital_system, severity
        )
        
        if hospital and doctor:
            if conflict_info:
                print(f"  Note: {conflict_info}")
            print(f"  Ambulance {ambulance} assigned")
            print(f"  Route: {' -> '.join(path)}")
            print(f"  Total Time: {time_taken:.1f} units (to hospital)")
            print(f"  Hospital: {hospital.name}")
            print(f"  Doctor: {doctor}")
        else:
            print(f"  Error: {conflict_info if conflict_info else 'No suitable hospital/doctor available'}")
            print(f"  Ambulance {ambulance} assigned (transport only)")
            print(f"  Route: {' -> '.join(path)}")
            print(f"  Time: {time_taken:.1f} units")
        print()
    
    print("=== Final Hospital Status ===")
    print(hospital_system.get_system_status())
    print()
    
    # Demonstrate redirection scenario
    print("=== Hospital Redirection Demonstration ===")
    demonstrate_redirection(city, hospital_system, ambulances)


def print_traffic_status(city):
    """Print current traffic and signal status"""
    for edge_key, density in city.traffic_density.items():
        from_node, to_node = edge_key
        base_weight = None
        for neighbor, weight in city.graph.get(from_node, []):
            if neighbor == to_node:
                base_weight = weight
                break
        
        if base_weight:
            current_weight = city.get_current_weight(from_node, to_node, base_weight)
            signal = city.traffic_signals.get(edge_key)
            signal_status = f"Signal: {signal['current_phase']}" if signal else "No signal"
            traffic_level = "Light" if density < 1.0 else "Heavy" if density > 1.5 else "Normal"
            print(f"  {from_node} -> {to_node}: Base {base_weight}, Current {current_weight:.1f}, Traffic: {traffic_level}, {signal_status}")


def demonstrate_redirection(city, hospital_system, ambulances):
    """Demonstrate hospital redirection when primary hospital is full"""
    print("Simulating full hospital scenario...")
    
    # Fill up Hospital 1 (City General)
    hospital1 = hospital_system.hospitals["H1"]
    original_capacity = hospital1.capacity
    hospital1.capacity = 0  # Make it full
    
    print(f"{hospital1.name} is now at full capacity")
    print()
    
    # Try to dispatch a critical patient
    patient_location = "E"
    severity = PatientSeverity.CRITICAL
    
    print(f"Critical patient at {patient_location} needs hospital:")
    ambulance, time_taken, path, hospital, doctor, conflict_info = assign_ambulance(
        city, ambulances, patient_location, hospital_system, severity
    )
    
    if hospital and doctor:
        print(f"  Redirected to: {hospital.name}")
        print(f"  Doctor assigned: {doctor}")
        print(f"  Total time: {time_taken:.1f} units")
    else:
        print(f"  No suitable hospital available")
    
    # Restore capacity
    hospital1.capacity = original_capacity
    print()
    print("Hospital capacity restored.")


def demonstrate_scenarios(city, hospital_system, ambulances):
    """Demonstrate different traffic scenarios"""
    print("\nScenario 1: Rush hour traffic")
    # Simulate rush hour
    for edge_key in city.traffic_density:
        city.traffic_density[edge_key] = min(city.traffic_density[edge_key] * 1.5, 3.0)
    
    ambulance, time_taken, path, hospital, doctor, conflict_info = assign_ambulance(
        city, ambulances, "E", hospital_system, PatientSeverity.URGENT
    )
    print(f"  Rush hour - Ambulance: {ambulance}, Time: {time_taken:.1f}, Hospital: {hospital.name if hospital else 'None'}")

    print("\nScenario 2: Clear roads")
    # Simulate clear roads
    for edge_key in city.traffic_density:
        city.traffic_density[edge_key] = 0.5
    
    ambulance, time_taken, path, hospital, doctor, conflict_info = assign_ambulance(
        city, ambulances, "E", hospital_system, PatientSeverity.MODERATE
    )
    print(f"  Clear roads - Ambulance: {ambulance}, Time: {time_taken:.1f}, Hospital: {hospital.name if hospital else 'None'}")


if __name__ == "__main__":
    main()
