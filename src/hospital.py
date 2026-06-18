from enum import Enum
from typing import List, Dict, Optional, Tuple


class PatientSeverity(Enum):
    CRITICAL = 1    # Life-threatening, immediate attention required
    URGENT = 2      # Serious but not immediately life-threatening
    MODERATE = 3    # Requires medical attention but can wait
    MILD = 4        # Minor injuries/conditions


class DoctorSpecialty(Enum):
    EMERGENCY = "Emergency Medicine"
    TRAUMA = "Trauma Surgery"
    CARDIOLOGY = "Cardiology"
    GENERAL = "General Practice"
    ORTHOPEDIC = "Orthopedic Surgery"


class Doctor:
    def __init__(self, id: str, name: str, specialty: DoctorSpecialty, available: bool = True):
        self.id = id
        self.name = name
        self.specialty = specialty
        self.available = available
        self.current_patient = None
        self.treatment_time_remaining = 0
    
    def assign_patient(self, patient_id: str, treatment_time: int):
        """Assign a patient to this doctor"""
        self.available = False
        self.current_patient = patient_id
        self.treatment_time_remaining = treatment_time
    
    def update_availability(self):
        """Update doctor availability based on treatment time"""
        if self.treatment_time_remaining > 0:
            self.treatment_time_remaining -= 1
        elif not self.available:
            self.available = True
            self.current_patient = None
    
    def __str__(self):
        status = "Available" if self.available else f"Busy (Patient: {self.current_patient})"
        return f"Dr. {self.name} ({self.specialty.value}) - {status}"


class Hospital:
    def __init__(self, id: str, name: str, location: str, capacity: int):
        self.id = id
        self.name = name
        self.location = location
        self.capacity = capacity
        self.current_patients = 0
        self.doctors: Dict[str, Doctor] = {}
        self.waiting_list: List[Tuple[str, PatientSeverity]] = []
        self.specialties_required: Dict[DoctorSpecialty, int] = {}
    
    def add_doctor(self, doctor: Doctor):
        """Add a doctor to this hospital"""
        self.doctors[doctor.id] = doctor
        self.specialties_required[doctor.specialty] = self.specialties_required.get(doctor.specialty, 0) + 1
    
    def get_available_doctors(self, specialty: Optional[DoctorSpecialty] = None) -> List[Doctor]:
        """Get list of available doctors, optionally filtered by specialty"""
        available = []
        for doctor in self.doctors.values():
            if doctor.available:
                if specialty is None or doctor.specialty == specialty:
                    available.append(doctor)
        return available
    
    def can_accept_patient(self, severity: PatientSeverity) -> bool:
        """Check if hospital can accept a new patient"""
        if self.current_patients >= self.capacity:
            return False
        
        # For critical patients, ensure at least one emergency doctor is available
        if severity == PatientSeverity.CRITICAL:
            emergency_doctors = self.get_available_doctors(DoctorSpecialty.EMERGENCY)
            trauma_doctors = self.get_available_doctors(DoctorSpecialty.TRAUMA)
            return len(emergency_doctors) > 0 or len(trauma_doctors) > 0
        
        return True
    
    def assign_patient_to_doctor(self, patient_id: str, severity: PatientSeverity) -> Optional[Doctor]:
        """Assign patient to appropriate available doctor"""
        preferred_specialties = self._get_required_specialties(severity)
        
        for specialty in preferred_specialties:
            available_doctors = self.get_available_doctors(specialty)
            if available_doctors:
                doctor = available_doctors[0]  # Assign to first available
                treatment_time = self._get_treatment_time(severity)
                doctor.assign_patient(patient_id, treatment_time)
                self.current_patients += 1
                return doctor
        
        return None
    
    def _get_required_specialties(self, severity: PatientSeverity) -> List[DoctorSpecialty]:
        """Get required doctor specialties based on patient severity"""
        if severity == PatientSeverity.CRITICAL:
            return [DoctorSpecialty.EMERGENCY, DoctorSpecialty.TRAUMA]
        elif severity == PatientSeverity.URGENT:
            return [DoctorSpecialty.EMERGENCY, DoctorSpecialty.GENERAL]
        elif severity == PatientSeverity.MODERATE:
            return [DoctorSpecialty.GENERAL, DoctorSpecialty.ORTHOPEDIC]
        else:  # MILD
            return [DoctorSpecialty.GENERAL]
    
    def _get_treatment_time(self, severity: PatientSeverity) -> int:
        """Get estimated treatment time based on severity"""
        if severity == PatientSeverity.CRITICAL:
            return 30  # 30 time units
        elif severity == PatientSeverity.URGENT:
            return 20
        elif severity == PatientSeverity.MODERATE:
            return 15
        else:  # MILD
            return 10
    
    def update_all_doctors(self):
        """Update availability of all doctors"""
        for doctor in self.doctors.values():
            doctor.update_availability()
    
    def get_bed_availability(self) -> int:
        """Get number of available beds"""
        return self.capacity - self.current_patients
    
    def __str__(self):
        available_doctors = len([d for d in self.doctors.values() if d.available])
        return (f"{self.name} ({self.location}) - Beds: {self.get_bed_availability()}/{self.capacity}, "
                f"Available Doctors: {available_doctors}/{len(self.doctors)}")


class HospitalSystem:
    def __init__(self):
        self.hospitals: Dict[str, Hospital] = {}
    
    def add_hospital(self, hospital: Hospital):
        """Add a hospital to the system"""
        self.hospitals[hospital.id] = hospital
    
    def find_best_hospital(self, patient_location: str, severity: PatientSeverity, 
                          graph, max_distance: float = float('inf')) -> Optional[Hospital]:
        """Find the best hospital for a patient based on availability and distance"""
        suitable_hospitals = []
        
        for hospital in self.hospitals.values():
            if hospital.can_accept_patient(severity):
                # Calculate distance from patient location to hospital
                try:
                    from src.routing import dijkstra
                    distances, _ = dijkstra(graph, patient_location)
                    distance = distances.get(hospital.location, float('inf'))
                    
                    if distance <= max_distance:
                        suitable_hospitals.append((hospital, distance))
                except:
                    # If graph routing fails, use hospital directly
                    suitable_hospitals.append((hospital, 0))
        
        if not suitable_hospitals:
            return None
        
        # Sort by distance (closest first) then by availability
        suitable_hospitals.sort(key=lambda x: (x[1], -x[0].get_bed_availability()))
        return suitable_hospitals[0][0]
    
    def redirect_to_next_hospital(self, patient_location: str, severity: PatientSeverity,
                                 excluded_hospital_id: str, graph) -> Optional[Hospital]:
        """Find next best hospital excluding a specific hospital"""
        suitable_hospitals = []
        
        for hospital in self.hospitals.values():
            if (hospital.id != excluded_hospital_id and 
                hospital.can_accept_patient(severity)):
                try:
                    from src.routing import dijkstra
                    distances, _ = dijkstra(graph, patient_location)
                    distance = distances.get(hospital.location, float('inf'))
                    suitable_hospitals.append((hospital, distance))
                except:
                    suitable_hospitals.append((hospital, 0))
        
        if not suitable_hospitals:
            return None
        
        suitable_hospitals.sort(key=lambda x: x[1])
        return suitable_hospitals[0][0]
    
    def get_system_status(self) -> str:
        """Get overall system status"""
        status = "=== Hospital System Status ===\n"
        for hospital in self.hospitals.values():
            status += f"{hospital}\n"
        return status
