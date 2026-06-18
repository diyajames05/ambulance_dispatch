import os
import time
from typing import List, Dict, Tuple, Optional
from src.hospital import Hospital, PatientSeverity, DoctorSpecialty


class Colors:
    """Terminal color codes for aesthetic display"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

    # Background colors
    BG_RED = '\033[101m'
    BG_GREEN = '\033[102m'
    BG_YELLOW = '\033[103m'
    BG_BLUE = '\033[104m'
    BG_WHITE = '\033[107m'
    WHITE = '\033[97m'


class ISSCalculator:
    """Injury Severity Score calculator and classifier"""

    @staticmethod
    def get_iss_description(score: int) -> Tuple[str, PatientSeverity]:
        """Convert simplified ISS score (0-6) to severity description and PatientSeverity enum"""
        if score == 6:
            return "Fatal - Immediate death expected", PatientSeverity.CRITICAL
        elif score == 5:
            return "Critical - Life threatening", PatientSeverity.CRITICAL
        elif score == 4:
            return "Severe - Major injury", PatientSeverity.URGENT
        elif score == 3:
            return "Serious - Significant injury", PatientSeverity.MODERATE
        elif score == 2:
            return "Moderate - Medical care needed", PatientSeverity.MODERATE
        elif score == 1:
            return "Minor - Basic treatment", PatientSeverity.MILD
        else:  # score == 0
            return "Minimal - First aid only", PatientSeverity.MILD

    @staticmethod
    def display_iss_scale():
        """Display the simplified ISS scale with descriptions"""
        print(Colors.CYAN + "\n" + "="*50)
        print("INJURY SEVERITY SCORE (0-6) CLASSIFICATION")
        print("="*50 + Colors.END)

        scale_data = [
            (6, "Fatal", Colors.BG_RED + Colors.WHITE),
            (5, "Critical", Colors.RED),
            (4, "Severe", Colors.YELLOW),
            (3, "Serious", Colors.BLUE),
            (2, "Moderate", Colors.GREEN),
            (1, "Minor", Colors.CYAN),
            (0, "Minimal", Colors.WHITE)
        ]

        for score, label, color in scale_data:
            desc, _ = ISSCalculator.get_iss_description(score)
            print(f"{color}ISS {score}: {label:8s} - {desc}{Colors.END}")

        print(Colors.CYAN + "="*50 + Colors.END)


class HospitalRanker:
    """Real-time hospital ranking system"""

    @staticmethod
    def rank_hospitals(patient_location: str, severity: PatientSeverity,
                     hospital_system, graph) -> List[Tuple[Hospital, float, Dict]]:
        """Rank hospitals by total travel time and availability"""
        rankings = []

        for hospital in hospital_system.hospitals.values():
            if hospital.can_accept_patient(severity):
                try:
                    from src.routing import dijkstra
                    distances, _ = dijkstra(graph, patient_location)
                    travel_time = distances.get(hospital.location, float('inf'))

                    if travel_time != float('inf'):
                        # Calculate hospital processing time
                        processing_time = HospitalRanker._estimate_processing_time(hospital, severity)
                        total_time = travel_time + processing_time

                        # Get available doctors
                        available_doctors = hospital.get_available_doctors()
                        doctor_info = {
                            'count': len(available_doctors),
                            'specialties': list(set(d.specialty for d in available_doctors))
                        }

                        rankings.append((hospital, total_time, doctor_info))
                except Exception as e:
                    print(f"Error calculating route to {hospital.name}: {e}")

        # Sort by total time (fastest first)
        rankings.sort(key=lambda x: x[1])
        return rankings

    @staticmethod
    def _estimate_processing_time(hospital: Hospital, severity: PatientSeverity) -> float:
        """Estimate hospital processing time based on current load"""
        base_times = {
            PatientSeverity.CRITICAL: 15,
            PatientSeverity.URGENT: 10,
            PatientSeverity.MODERATE: 8,
            PatientSeverity.MILD: 5
        }

        base_time = base_times.get(severity, 10)

        # Add delay based on current patient load
        load_factor = hospital.current_patients / hospital.capacity
        load_delay = load_factor * 10  # Up to 10 extra units for full hospitals

        return base_time + load_delay


class InteractiveUI:
    """Interactive terminal user interface"""

    def __init__(self):
        self.clear_screen()

    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_header(self):
        """Display the application header"""
        print(Colors.HEADER + Colors.BOLD)
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║          SMART AMBULANCE DISPATCH SYSTEM v2.0                ║")
        print("║         Real-time Hospital Ranking & Triage System            ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print(Colors.END)
        print()

    def display_main_menu(self):
        """Display the main menu options"""
        print(Colors.CYAN + "MAIN MENU" + Colors.END)
        print(Colors.BLUE + "─" * 40 + Colors.END)
        print("1.  Emergency Dispatch")
        print("2.  View Hospital Status")
        print("3.  View Traffic Conditions")
        print("4.  ISS Reference Guide")
        print("5.  Exit")
        print(Colors.BLUE + "─" * 40 + Colors.END)

        try:
            choice = int(input("\nSelect an option (1-5): "))
            return choice
        except ValueError:
            return 0

    def get_patient_location(self, available_locations: List[str]) -> str:
        """Get patient location from user"""
        print(Colors.YELLOW + "\n📍 PATIENT LOCATION" + Colors.END)
        print(Colors.BLUE + "─" * 30 + Colors.END)

        for i, location in enumerate(available_locations, 1):
            print(f"{i}. {location}")

        while True:
            try:
                choice = int(input(f"\nSelect location (1-{len(available_locations)}): "))
                if 1 <= choice <= len(available_locations):
                    return available_locations[choice - 1]
                else:
                    print(Colors.RED + "Invalid choice. Please try again." + Colors.END)
            except ValueError:
                print(Colors.RED + "Please enter a valid number." + Colors.END)

    def get_iss_score(self) -> int:
        """Get simplified ISS score from user with validation"""
        print(Colors.YELLOW + "\n🏥 INJURY SEVERITY SCORE (ISS 0-6)" + Colors.END)
        print(Colors.BLUE + "─" * 40 + Colors.END)

        # Show the scale with short descriptions
        print("0: Minimal - First aid only")
        print("1: Minor - Basic treatment")
        print("2: Moderate - Medical care needed")
        print("3: Serious - Significant injury")
        print("4: Severe - Major injury")
        print("5: Critical - Life threatening")
        print("6: Fatal - Immediate death expected")
        print(Colors.BLUE + "─" * 40 + Colors.END)

        while True:
            try:
                score = int(input("Enter ISS score (0-6): "))
                if 0 <= score <= 6:
                    return score
                else:
                    print(Colors.RED + "ISS score must be between 0 and 6." + Colors.END)
            except ValueError:
                print(Colors.RED + "Please enter a valid number." + Colors.END)

    def display_hospital_rankings(self, rankings: List[Tuple[Hospital, float, Dict]]):
        """Display ranked hospital options"""
        print(Colors.GREEN + "\n🏥 AVAILABLE HOSPITALS (RANKED BY TOTAL TIME)" + Colors.END)
        print(Colors.BLUE + "─" * 60 + Colors.END)

        if not rankings:
            print(Colors.RED + "No suitable hospitals available at this time." + Colors.END)
            return None

        print(f"{'Rank':<5} {'Hospital':<25} {'Total Time':<12} {'Travel':<8} {'Processing':<12} {'Doctors':<8}")
        print(Colors.BLUE + "─" * 70 + Colors.END)

        for i, (hospital, total_time, doctor_info) in enumerate(rankings, 1):
            # Extract travel and processing time
            if total_time == float('inf'):
                total_display = "∞"
                travel_display = "∞"
                processing_display = "∞"
                time_color = Colors.RED
            else:
                total_display = f"{total_time:.1f}"
                travel_time = total_time - (total_time * 0.3)  # Approximate
                processing_time = total_time - travel_time
                travel_display = f"{travel_time:.1f}"
                processing_display = f"{processing_time:.1f}"

                # Color code based on time
                if total_time < 10:
                    time_color = Colors.GREEN
                elif total_time < 20:
                    time_color = Colors.YELLOW
                else:
                    time_color = Colors.RED

            print(f"{i:<5} {hospital.name[:24]:<25} {time_color}{total_display}{Colors.END:<11} "
                  f"{travel_display:<8} {processing_display:<12} {doctor_info['count']:<8}")

            # Show doctor specialties
            if doctor_info['specialties']:
                specialties = ", ".join(s.value.split()[0] for s in doctor_info['specialties'])
                print(f"      {Colors.CYAN}Available: {specialties}{Colors.END}")
            print()

        # Get user selection
        while True:
            try:
                choice = int(input(f"Select hospital (1-{len(rankings)}) or 0 to cancel: "))
                if choice == 0:
                    return None
                elif 1 <= choice <= len(rankings):
                    return rankings[choice - 1][0]
                else:
                    print(Colors.RED + "Invalid choice. Please try again." + Colors.END)
            except ValueError:
                print(Colors.RED + "Please enter a valid number." + Colors.END)

    def display_dispatch_result(self, ambulance: str, route: List[str], total_time: float,
                             hospital: Hospital, doctor, iss_score: int, conflict_info: str = None):
        """Display the dispatch results"""
        print(Colors.GREEN + "\n DISPATCH CONFIRMED" + Colors.END)
        print(Colors.BLUE + "═" * 50 + Colors.END)

        # Conflict notification if any
        if conflict_info:
            print(f"{Colors.YELLOW}ℹ  NOTE: {conflict_info}{Colors.END}")
            print(Colors.BLUE + "─" * 50 + Colors.END)

        # Patient info
        desc, _ = ISSCalculator.get_iss_description(iss_score)
        print(f" Patient: ISS {iss_score} ({desc})")

        # Ambulance info
        print(f" Ambulance: {ambulance}")
        print(f"  Route: {' → '.join(route)}")

        # Hospital info
        print(f" Hospital: {hospital.name}")
        print(f"  Doctor: {doctor}")
        print(f"⏱  Total Time: {total_time:.1f} units")

        print(Colors.BLUE + "═" * 50 + Colors.END)

    def display_hospital_status(self, hospital_system):
        """Display current hospital system status"""
        print(Colors.CYAN + "\n HOSPITAL SYSTEM STATUS" + Colors.END)
        print(Colors.BLUE + "─" * 50 + Colors.END)

        for hospital in hospital_system.hospitals.values():
            available_beds = hospital.get_bed_availability()
            available_doctors = len([d for d in hospital.doctors.values() if d.available])
            total_doctors = len(hospital.doctors)

            # Color code based on availability
            if available_beds > 20:
                bed_color = Colors.GREEN
            elif available_beds > 10:
                bed_color = Colors.YELLOW
            else:
                bed_color = Colors.RED

            if available_doctors > total_doctors * 0.5:
                doctor_color = Colors.GREEN
            elif available_doctors > 0:
                doctor_color = Colors.YELLOW
            else:
                doctor_color = Colors.RED

            print(f"\n{Colors.BOLD}{hospital.name}{Colors.END}")
            print(f"   Location: {hospital.location}")
            print(f"   Beds: {bed_color}{available_beds}/{hospital.capacity}{Colors.END}")
            print(f"   Doctors: {doctor_color}{available_doctors}/{total_doctors}{Colors.END}")

            # Show available doctors by specialty
            available_by_specialty = {}
            for doctor in hospital.doctors.values():
                if doctor.available:
                    specialty = doctor.specialty.value.split()[0]
                    available_by_specialty[specialty] = available_by_specialty.get(specialty, 0) + 1

            if available_by_specialty:
                specialties = ", ".join(f"{k}: {v}" for k, v in available_by_specialty.items())
                print(f"   Available: {specialties}")

    def display_traffic_status(self, city):
        """Display current traffic conditions"""
        print(Colors.CYAN + "\n🚦 TRAFFIC CONDITIONS" + Colors.END)
        print(Colors.BLUE + "─" * 50 + Colors.END)

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

                # Traffic level color coding
                if density < 1.0:
                    traffic_color = Colors.GREEN
                    traffic_level = "Light"
                elif density > 1.5:
                    traffic_color = Colors.RED
                    traffic_level = "Heavy"
                else:
                    traffic_color = Colors.YELLOW
                    traffic_level = "Normal"

                # Signal color coding
                if signal:
                    signal_color = Colors.GREEN if signal['current_phase'] == 'green' else Colors.RED
                    signal_status = f"{signal_color}Signal: {signal['current_phase'].upper()}{Colors.END}"
                else:
                    signal_status = "No signal"

                print(f"  {from_node} → {to_node}: {traffic_color}{traffic_level}{Colors.END} "
                      f"(Base: {base_weight}, Current: {current_weight:.1f}) {signal_status}")

    def wait_for_continue(self):
        """Wait for user to press enter to continue"""
        input(Colors.YELLOW + "\nPress Enter to continue..." + Colors.END)

    def display_error(self, message: str):
        """Display an error message"""
        print(Colors.RED + f" ERROR: {message}" + Colors.END)

    def display_success(self, message: str):
        """Display a success message"""
        print(Colors.GREEN + f" {message}" + Colors.END)
