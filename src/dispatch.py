from src.routing import dijkstra, reconstruct_path
from src.hospital import HospitalSystem, PatientSeverity


def check_doctor_conflict(hospital, severity):
    """Check if there's a doctor availability conflict"""
    available_doctors = hospital.get_available_doctors()
    
    if not available_doctors:
        return "No doctors available at this hospital"
    
    # Check if required specialty is available
    required_specialties = {
        PatientSeverity.CRITICAL: ["Emergency", "Trauma"],
        PatientSeverity.URGENT: ["Emergency", "General"],
        PatientSeverity.MODERATE: ["General", "Orthopedic"],
        PatientSeverity.MILD: ["General"]
    }.get(severity, [])
    
    available_specialties = [d.specialty.value.split()[0] for d in available_doctors]
    
    # Check if any required specialty is available
    for req_specialty in required_specialties:
        if req_specialty in available_specialties:
            return None  # No conflict
    
    return f"No doctor with required specialty available (Need: {', '.join(required_specialties)})"


def resolve_conflict(hospital_system, location, severity, rankings):
    """Resolve doctor availability conflict by finding alternative hospital"""
    # Try other hospitals in ranking
    for i, (hospital, total_time, doctor_info) in enumerate(rankings[1:], 1):
        conflict = check_doctor_conflict(hospital, severity)
        
        if not conflict:
            return hospital, f"Alternative found: {hospital.name} (Rank {i+1})"
    
    # If no hospital in rankings works, try all hospitals
    for hospital in hospital_system.hospitals.values():
        if hospital.can_accept_patient(severity):
            available_doctors = hospital.get_available_doctors()
            if available_doctors:
                return hospital, f"Emergency option: {hospital.name}"
    
    return None, "No suitable hospital available"


def assign_ambulance(graph, ambulances, patient_location, hospital_system=None, severity=None, target_hospital=None):
    best_time = float('inf')
    best_ambulance = None
    best_path = []
    conflict_info = None

    for ambulance in ambulances:
        distances, previous = dijkstra(graph, ambulance)

        if distances[patient_location] < best_time:
            best_time = distances[patient_location]
            best_ambulance = ambulance
            best_path = reconstruct_path(previous, ambulance, patient_location)

    # If hospital system is provided, find best hospital
    if hospital_system and severity:
        if not target_hospital:
            from src.ui import HospitalRanker
            rankings = HospitalRanker.rank_hospitals(patient_location, severity, hospital_system, graph)
            
            if rankings:
                # Try to assign to best hospital
                target_hospital, total_time, doctor_info = rankings[0]
            else:
                return best_ambulance, best_time, best_path, None, None, "No suitable hospitals available"
        else:
            # Manually selected hospital
            hospital_distances, _ = dijkstra(graph, patient_location)
            hospital_time = hospital_distances.get(target_hospital.location, float('inf'))
            total_time = best_time + hospital_time
            rankings = [] # No rankings needed for manual selection
        
        if target_hospital:
            # Check for doctor availability conflicts
            conflict = check_doctor_conflict(target_hospital, severity)
            
            if conflict:
                # Try to resolve conflict if it wasn't manually selected
                # Or just report it if it was manually selected?
                # Usually if user selects it, we should still check.
                if rankings: # Came from automatic selection
                    resolved_hospital, resolution_info = resolve_conflict(
                        hospital_system, patient_location, severity, rankings
                    )
                    
                    if resolved_hospital:
                        target_hospital = resolved_hospital
                        conflict_info = resolution_info
                        
                        # Calculate new total time
                        hospital_distances, _ = dijkstra(graph, patient_location)
                        new_hospital_time = hospital_distances.get(resolved_hospital.location, float('inf'))
                        total_time = best_time + new_hospital_time
                    else:
                        return best_ambulance, best_time, best_path, None, None, f"CONFLICT: {conflict}"
                else:
                    # Manually selected, just report conflict
                    return best_ambulance, total_time, best_path, None, None, f"CONFLICT: {conflict}"
            
            # Try to assign patient to doctor
            assigned_doctor = target_hospital.assign_patient_to_doctor(f"Patient_{patient_location}", severity)
            
            if assigned_doctor:
                return best_ambulance, total_time, best_path, target_hospital, assigned_doctor, conflict_info
            else:
                return best_ambulance, total_time, best_path, None, None, "Failed to assign doctor"

    return best_ambulance, best_time, best_path, target_hospital, None, conflict_info


def prioritize_patients(patients):
    """Sort patients by severity (critical first)"""
    return sorted(patients, key=lambda p: p[1].value)