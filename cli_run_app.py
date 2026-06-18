from src.graph import Graph
from src.dispatch import assign_ambulance
from src.routing import simulate_traffic_changes
from src.hospital import Hospital, Doctor, DoctorSpecialty, PatientSeverity, HospitalSystem
from src.ui import InteractiveUI, ISSCalculator, HospitalRanker, Colors
import time
import threading


class InteractiveDispatchSystem:
    """Main interactive dispatch system"""
    
    def __init__(self):
        self.ui = InteractiveUI()
        self.city = None
        self.hospital_system = None
        self.ambulances = ["A", "B"]
        self.running = True
        
        # Initialize system
        self._initialize_system()
    
    def _initialize_system(self):
        """Initialize city and hospital system"""
        self.city = self._build_city()
        self.hospital_system = self._build_hospital_system()
        
        # Start background traffic simulation
        self._start_traffic_simulation()
    
    def _build_city(self):
        """Build the city graph with traffic and signals"""
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

        # Set initial traffic densities
        city.set_traffic_density("A", "B", 1.2)
        city.set_traffic_density("B", "C", 1.8)
        city.set_traffic_density("A", "D", 0.9)
        city.set_traffic_density("D", "C", 1.3)
        city.set_traffic_density("C", "E", 1.6)
        city.set_traffic_density("B", "E", 1.1)

        # Add traffic signals
        current_time = time.time()
        city.add_traffic_signal("A", "B", {
            'cycle_time': 60,
            'green_time': 30,
            'current_phase': 'green',
            'phase_start': current_time
        })
        
        city.add_traffic_signal("C", "E", {
            'cycle_time': 90,
            'green_time': 45,
            'current_phase': 'red',
            'phase_start': current_time
        })

        return city
    
    def _build_hospital_system(self):
        """Build the hospital system"""
        hospital_system = HospitalSystem()
        
        # Create hospitals
        hospital1 = Hospital("H1", "City General Hospital", "C", capacity=50)
        hospital2 = Hospital("H2", "St. Mary's Medical Center", "E", capacity=30)
        hospital3 = Hospital("H3", "Emergency Care Unit", "A", capacity=20)
        
        # Add doctors to Hospital 1
        hospital1.add_doctor(Doctor("D1", "Dr. Smith", DoctorSpecialty.EMERGENCY))
        hospital1.add_doctor(Doctor("D2", "Dr. Johnson", DoctorSpecialty.TRAUMA))
        hospital1.add_doctor(Doctor("D3", "Dr. Williams", DoctorSpecialty.GENERAL))
        hospital1.add_doctor(Doctor("D8", "Dr. Anderson", DoctorSpecialty.ORTHOPEDIC))
        
        # Add doctors to Hospital 2
        hospital2.add_doctor(Doctor("D4", "Dr. Brown", DoctorSpecialty.EMERGENCY))
        hospital2.add_doctor(Doctor("D5", "Dr. Davis", DoctorSpecialty.GENERAL))
        hospital2.add_doctor(Doctor("D9", "Dr. Taylor", DoctorSpecialty.TRAUMA))
        
        # Add doctors to Hospital 3
        hospital3.add_doctor(Doctor("D6", "Dr. Miller", DoctorSpecialty.EMERGENCY))
        hospital3.add_doctor(Doctor("D7", "Dr. Wilson", DoctorSpecialty.ORTHOPEDIC))
        
        hospital_system.add_hospital(hospital1)
        hospital_system.add_hospital(hospital2)
        hospital_system.add_hospital(hospital3)
        
        return hospital_system
    
    def _start_traffic_simulation(self):
        """Start background traffic simulation"""
        def simulate():
            while self.running:
                time.sleep(5)  # Update every 5 seconds
                if self.city:
                    simulate_traffic_changes(self.city)
        
        traffic_thread = threading.Thread(target=simulate, daemon=True)
        traffic_thread.start()
    
    def run(self):
        """Main application loop"""
        self.ui.clear_screen()
        self.ui.display_header()
        
        print(f"{Colors.GREEN}Welcome to the Smart Ambulance Dispatch System!{Colors.END}")
        print("This tool helps dispatchers find the best hospital for patients based on:")
        print(" - 🚑 Real-time ambulance travel times")
        print(" - 🚥 Current city traffic and signal conditions")
        print(" - 🏥 Hospital bed capacity and doctor availability")
        print(" - 🩺 Patient Injury Severity Score (ISS)")
        print()
        input(f"{Colors.YELLOW}Press Enter to start the system...{Colors.END}")
        
        while self.running:
            try:
                self.ui.clear_screen()
                self.ui.display_header()
                
                choice = self.ui.display_main_menu()
                
                if choice == 1:
                    self._handle_emergency_dispatch()
                elif choice == 2:
                    self._handle_hospital_status()
                elif choice == 3:
                    self._handle_traffic_status()
                elif choice == 4:
                    self._handle_iss_reference()
                elif choice == 5:
                    self._handle_exit()
                else:
                    self.ui.display_error("Invalid option. Please try again.")
                    self.ui.wait_for_continue()
                    
            except KeyboardInterrupt:
                self._handle_exit()
            except Exception as e:
                self.ui.display_error(f"An error occurred: {e}")
                self.ui.wait_for_continue()
    
    def _handle_emergency_dispatch(self):
        """Handle emergency dispatch workflow"""
        self.ui.clear_screen()
        self.ui.display_header()
        
        print(Colors.RED + Colors.BOLD + "🚨 EMERGENCY DISPATCH" + Colors.END)
        print(Colors.BLUE + "─" * 40 + Colors.END)
        
        # Get patient location
        patient_location = self.ui.get_patient_location(list(self.city.get_nodes()))
        
        # Get ISS score
        iss_score = self.ui.get_iss_score()
        severity = ISSCalculator.get_iss_description(iss_score)[1]
        
        # Show severity classification
        desc, _ = ISSCalculator.get_iss_description(iss_score)
        print(f"\n{Colors.YELLOW}Severity: {desc}{Colors.END}")
        
        # Get ranked hospitals
        rankings = HospitalRanker.rank_hospitals(
            patient_location, severity, self.hospital_system, self.city
        )
        
        if not rankings:
            self.ui.display_error("No suitable hospitals available for this severity level.")
            self.ui.wait_for_continue()
            return
        
        # Display hospital options
        selected_hospital = self.ui.display_hospital_rankings(rankings)
        
        if selected_hospital:
            # Assign ambulance and dispatch
            ambulance, total_time, route, hospital, doctor, conflict_info = assign_ambulance(
                self.city, self.ambulances, patient_location, 
                self.hospital_system, severity, target_hospital=selected_hospital
            )
            
            if hospital and doctor:
                self.ui.display_dispatch_result(
                    ambulance, route, total_time, hospital, doctor, iss_score, conflict_info
                )
            else:
                self.ui.display_error(f"Unable to complete dispatch - {conflict_info if conflict_info else 'no available resources.'}")
        else:
            self.ui.display_error("Dispatch cancelled.")
        
        self.ui.wait_for_continue()
    
    def _handle_hospital_status(self):
        """Handle hospital status display"""
        self.ui.clear_screen()
        self.ui.display_header()
        self.ui.display_hospital_status(self.hospital_system)
        self.ui.wait_for_continue()
    
    def _handle_traffic_status(self):
        """Handle traffic status display"""
        self.ui.clear_screen()
        self.ui.display_header()
        self.ui.display_traffic_status(self.city)
        self.ui.wait_for_continue()
    
    def _handle_iss_reference(self):
        """Handle ISS reference guide"""
        self.ui.clear_screen()
        self.ui.display_header()
        ISSCalculator.display_iss_scale()
        self.ui.wait_for_continue()
    
    def _handle_exit(self):
        """Handle application exit"""
        self.running = False
        self.ui.clear_screen()
        print(Colors.GREEN + "Thank you for using Smart Ambulance Dispatch System!")
        print("Stay safe! 🚑" + Colors.END)
        exit()


def main():
    """Main entry point"""
    try:
        system = InteractiveDispatchSystem()
        system.run()
    except Exception as e:
        print(Colors.RED + f"Fatal error: {e}" + Colors.END)
        print("Please restart the application.")


if __name__ == "__main__":
    main()
