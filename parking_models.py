"""
Parking Management System - Data Models Module

This module defines the core data structures and business logic for the parking management system.
It includes enums for vehicle types, customer types, and sections, as well as classes for
Vehicle, Slot, and ParkingLot. The ParkingLot class handles slot allocation and release
with priority rules, time limits, and fee calculations.

Key Features:
- Support for different vehicle types (Small, Medium, Large) and customer types (Regular, VIP)
- Time-based parking with limits (4 hours for regular, 8 hours for VIP)
- Fee calculation based on parking duration
- Priority allocation for VIP customers and EV vehicles
- Thread-safe operations using locks for concurrent access
- Real-world rules like EV charging spots and VIP sections

Classes:
- Vehicle: Represents a parked vehicle with type, customer type, and license plate
- Slot: Represents a parking slot with properties like level, section, vehicle type support, etc.
- ParkingLot: Main class managing all slots, allocation, and release operations
"""

from enum import Enum
from datetime import datetime, timedelta
import threading
import uuid

class VehicleType(Enum):
    """Enumeration of supported vehicle types."""
    SMALL = "Small"  # e.g., motorcycles, compact cars
    MEDIUM = "Medium"  # e.g., sedans, SUVs
    LARGE = "Large"  # e.g., trucks, vans

class CustomerType(Enum):
    """Enumeration of customer types with different privileges."""
    REGULAR = "Regular"  # Standard customers with 24-hour limit
    VIP = "VIP"  # Premium customers with 1-week limit and priority

class Section(Enum):
    """Enumeration of parking sections."""
    REGULAR = "Regular"  # Standard parking section
    VIP = "VIP"  # Premium section for VIP customers
    EV = "EV"  # Electric vehicle charging section

class ParkingRules:
    """
    Comprehensive parking rules and policies.
    """

    # Time limits in hours
    TIME_LIMITS = {
        CustomerType.REGULAR: 24,  # 24 hours
        CustomerType.VIP: 720      # 30 days (monthly membership)
    }

    # Daily rates in rupees
    DAILY_RATES = {
        VehicleType.SMALL: 50.0,
        VehicleType.MEDIUM: 100.0,
        VehicleType.LARGE: 150.0
    }

    # Monthly membership pricing (30 days at daily rate with 30% discount)
    MONTHLY_MEMBERSHIP_RATES = {
        VehicleType.SMALL: round(50.0 * 30 * 0.7, 2),   # ₹1,050 (₹1,500 - 30% discount)
        VehicleType.MEDIUM: round(100.0 * 30 * 0.7, 2), # ₹2,100 (₹3,000 - 30% discount)
        VehicleType.LARGE: round(150.0 * 30 * 0.7, 2)   # ₹3,150 (₹4,500 - 30% discount)
    }

    # Operating hours - 24/7 service (no restrictions)
    OPERATING_HOURS = {
        '24_7_service': True
    }

    # Re-entry rules
    RE_ENTRY_RULES = {
        'max_re_entries': 3,  # Maximum re-entries per day
        're_entry_window': 24,  # Hours within which re-entry is allowed
        're_entry_fee': 20.0   # Additional fee for re-entry in rupees
    }

    # Restrictions
    RESTRICTIONS = {
        'max_overstay_penalty': 500.0,  # Maximum penalty for overstay in rupees
        'penalty_per_hour': 25.0,       # Penalty per hour overstay
        'vip_reservation_hours': 2,     # Hours in advance VIP can reserve
        'ev_charging_limit': 8,         # Maximum charging time in hours
        'disabled_access_slots': 5,     # Number of accessible slots per level
        'motorcycle_only_zones': True,  # Small vehicles only in certain areas
        'commercial_vehicle_restrictions': True,  # Large vehicles restricted during peak hours
        'peak_hours': ['09:00-11:00', '17:00-19:00'],  # Peak hours for restrictions
        'max_continuous_parking': 72,   # Maximum continuous parking hours
        'reservation_required': False,  # Whether reservation is required
        'payment_grace_period': 15      # Minutes to pay after exit
    }

    # Security and safety
    SECURITY_RULES = {
        'cctv_coverage': True,
        'emergency_alarms': True,
        'security_patrols': True,
        'vehicle_inspection': False,  # Random vehicle inspections
        'suspicious_activity_reporting': True,
        'lost_and_found': True,
        'emergency_vehicle_access': True
    }

    # Environmental policies
    ENVIRONMENTAL_POLICIES = {
        'ev_preferred_parking': True,
        'carbon_offset_program': True,
        'green_spaces': True,
        'solar_powered_lighting': True,
        'water_recycling': True
    }

    @classmethod
    def get_rules_text(cls):
        """Get formatted rules text for display."""
        return {
            'time_limits': f"""
            • Regular customers: {cls.TIME_LIMITS[CustomerType.REGULAR]} hours maximum
            • VIP customers: Monthly pass with unlimited parking for 30 days
            """.strip(),

            'pricing': f"""
            • Small vehicles: ₹{cls.DAILY_RATES[VehicleType.SMALL]}/day
            • Medium vehicles: ₹{cls.DAILY_RATES[VehicleType.MEDIUM]}/day
            • Large vehicles: ₹{cls.DAILY_RATES[VehicleType.LARGE]}/day
            • VIP Monthly Pass (unlimited parking):
              - Small: ₹{cls.MONTHLY_MEMBERSHIP_RATES[VehicleType.SMALL]}
              - Medium: ₹{cls.MONTHLY_MEMBERSHIP_RATES[VehicleType.MEDIUM]}
              - Large: ₹{cls.MONTHLY_MEMBERSHIP_RATES[VehicleType.LARGE]}
            """.strip(),

            'restrictions': f"""
            • 24/7 service - Open all day, every day
            • Maximum re-entries: {cls.RE_ENTRY_RULES['max_re_entries']} per day
            • Re-entry window: {cls.RE_ENTRY_RULES['re_entry_window']} hours
            • Peak hour restrictions: {', '.join(cls.RESTRICTIONS['peak_hours'])}
            • Payment grace period: {cls.RESTRICTIONS['payment_grace_period']} minutes
            • Maximum continuous parking: {cls.RESTRICTIONS['max_continuous_parking']} hours
            """.strip(),

            'policies': f"""
            • EV charging limit: {cls.RESTRICTIONS['ev_charging_limit']} hours
            • Overstay penalty: ₹{cls.RESTRICTIONS['penalty_per_hour']}/hour
            • Re-entry fee: ₹{cls.RE_ENTRY_RULES['re_entry_fee']}
            • Accessible parking available
            • CCTV surveillance active
            • Emergency vehicle priority access
            • VIP members get priority allocation and unlimited monthly parking
            • VIP passes are registered to license plates and valid for 30 days
            """.strip()
        }

class Vehicle:
    """
    Represents a vehicle in the parking system with enhanced policy tracking.
    """

    def __init__(self, vehicle_type, customer_type, license_plate):
        """
        Initialize a new vehicle.

        Args:
            vehicle_type (VehicleType): Type of the vehicle
            customer_type (CustomerType): Type of customer
            license_plate (str): License plate number
        """
        self.vehicle_type = vehicle_type
        self.customer_type = customer_type
        self.license_plate = license_plate
        self.ticket_id = str(uuid.uuid4())[:8].upper()  # Generate short unique ticket ID
        self.allocation_time = None  # Set when allocated

        # Policy tracking
        self.re_entry_count = 0
        self.last_re_entry = None
        self.total_overstay_penalty = 0.0
        self.warnings_issued = 0
        self.is_suspended = False
        self.suspension_reason = ""

        # Parking history
        self.parking_sessions = []  # List of (entry_time, exit_time, slot_id) tuples
        self.total_parking_time = 0  # Total hours parked
        self.total_fees_paid = 0.0

        # Special accommodations
        self.accessible_parking = False
        self.ev_charging = False
        self.reservation_id = None
        self.vip_pass_expiry = None  # For VIP monthly pass holders

    def can_re_enter(self) -> bool:
        """Check if vehicle can re-enter based on rules."""
        if self.re_entry_count >= ParkingRules.RE_ENTRY_RULES['max_re_entries']:
            return False

        if self.last_re_entry:
            hours_since_last = (datetime.now() - self.last_re_entry).total_seconds() / 3600
            if hours_since_last > ParkingRules.RE_ENTRY_RULES['re_entry_window']:
                self.re_entry_count = 0  # Reset counter after window

        return not self.is_suspended

    def record_re_entry(self):
        """Record a re-entry event."""
        self.re_entry_count += 1
        self.last_re_entry = datetime.now()

    def add_parking_session(self, entry_time: datetime, exit_time: datetime, slot_id: str):
        """Add a completed parking session."""
        duration_hours = (exit_time - entry_time).total_seconds() / 3600
        self.parking_sessions.append((entry_time, exit_time, slot_id))
        self.total_parking_time += duration_hours

    def get_re_entry_fee(self) -> float:
        """Calculate re-entry fee if applicable."""
        return ParkingRules.RE_ENTRY_RULES['re_entry_fee'] if self.re_entry_count > 0 else 0.0

    def issue_warning(self, reason: str):
        """Issue a warning to the vehicle owner."""
        self.warnings_issued += 1
        if self.warnings_issued >= 3:
            self.is_suspended = True
            self.suspension_reason = "Multiple violations"

    def __str__(self):
        """String representation of the vehicle."""
        return f"{self.vehicle_type.value} vehicle ({self.license_plate}) - {self.customer_type.value}"

class Slot:
    """
    Represents a parking slot in the system.

    Attributes:
        id (str): Unique slot identifier
        level (int): Floor level (1 or 2)
        section (Section): Section type (Regular/VIP/EV)
        vehicle_type (VehicleType): Supported vehicle type
        vehicle (Vehicle): Currently parked vehicle (None if empty)
        allocation_time (datetime): When current vehicle was allocated
        is_occupied (bool): Whether slot is currently occupied
    """

    def __init__(self, slot_id, level, section, vehicle_type):
        """
        Initialize a new parking slot.

        Args:
            slot_id (str): Unique identifier for the slot
            level (int): Floor level
            section (Section): Section type
            vehicle_type (VehicleType): Supported vehicle type
        """
        self.id = slot_id
        self.level = level
        self.section = section
        self.vehicle_type = vehicle_type
        self.vehicle = None
        self.allocation_time = None
        self.is_occupied = False

    def allocate(self, vehicle):
        """
        Allocate this slot to a vehicle.

        Args:
            vehicle (Vehicle): The vehicle to park

        Returns:
            bool: True if allocation successful, False otherwise
        """
        if self.is_occupied:
            return False

        self.vehicle = vehicle
        self.vehicle.allocation_time = datetime.now()
        self.allocation_time = self.vehicle.allocation_time
        self.is_occupied = True
        return True

    def release(self):
        """
        Release the slot (remove the vehicle).

        Returns:
            Vehicle: The vehicle that was parked (for receipt generation)
        """
        if not self.is_occupied:
            return None

        vehicle = self.vehicle
        self.vehicle = None
        # Note: Keep allocation_time for receipt generation, don't reset here
        self.is_occupied = False
        return vehicle

    def is_expired(self):
        """
        Check if the parked vehicle has exceeded the time limit.

        Returns:
            bool: True if expired, False otherwise
        """
        if not self.is_occupied or not self.allocation_time:
            return False

        # VIP with active pass never expires
        if (self.vehicle.customer_type == CustomerType.VIP and
            self.vehicle.vip_pass_expiry and
            datetime.now() < self.vehicle.vip_pass_expiry):
            return False

        # Regular: 24 hours, VIP without pass: 30 days
        time_limit = timedelta(hours=24) if self.vehicle.customer_type == CustomerType.REGULAR else timedelta(days=30)
        return datetime.now() - self.allocation_time > time_limit

    def calculate_fee(self):
        """
        Calculate parking fee based on duration and vehicle type, including overstay penalties.

        Pricing (in rupees):
        - Small vehicles: ₹50/day
        - Medium vehicles: ₹100/day
        - Large vehicles: ₹150/day

        VIP customers pay monthly membership fee (30 days at daily rate with 30% discount).
        Regular customers pay per day used.
        Overstay penalties: ₹25/hour after time limit.

        Returns:
            float: Parking fee in rupees
        """
        if not self.is_occupied or not self.allocation_time:
            return 0.0

        duration = datetime.now() - self.allocation_time
        days_used = max(1, duration.total_seconds() / (24 * 3600))  # At least 1 day

        # Daily rates in rupees based on vehicle type
        daily_rates = {
            VehicleType.SMALL: 50.0,
            VehicleType.MEDIUM: 100.0,
            VehicleType.LARGE: 150.0
        }

        daily_rate = daily_rates[self.vehicle.vehicle_type]

        # Check if VIP has active monthly pass
        if (self.vehicle.customer_type == CustomerType.VIP and
            self.vehicle.vip_pass_expiry and
            datetime.now() < self.vehicle.vip_pass_expiry):
            # VIP pass holders park for free
            base_fee = 0.0
        elif self.vehicle.customer_type == CustomerType.VIP:
            # VIP without active pass pays monthly membership fee
            base_fee = ParkingRules.MONTHLY_MEMBERSHIP_RATES[self.vehicle.vehicle_type]
        else:
            # Regular pays per day used
            base_fee = daily_rate * days_used

        # Calculate overstay penalty
        time_limit_hours = ParkingRules.TIME_LIMITS[self.vehicle.customer_type]
        time_limit = timedelta(hours=time_limit_hours)

        if duration > time_limit:
            overstay_hours = (duration - time_limit).total_seconds() / 3600
            penalty_rate = ParkingRules.RESTRICTIONS['penalty_per_hour']
            overstay_penalty = min(overstay_hours * penalty_rate,
                                 ParkingRules.RESTRICTIONS['max_overstay_penalty'])
            base_fee += overstay_penalty

        return round(base_fee, 2)

    def __str__(self):
        """String representation of the slot."""
        status = "Occupied" if self.is_occupied else "Empty"
        vehicle_info = f" - {self.vehicle}" if self.is_occupied else ""
        return f"Slot {self.id} (Level {self.level}, {self.section.value}, {self.vehicle_type.value}): {status}{vehicle_info}"

class ParkingLot:
    """
    Main class managing the entire parking lot system.

    This class handles slot creation, allocation, release, and provides methods
    for finding available slots based on priority rules.

    Attributes:
        slots (dict): Dictionary of all slots keyed by slot ID
        lock (threading.Lock): Thread lock for concurrent access
    """

    def __init__(self):
        """
        Initialize the parking lot with predefined slots.

        Creates slots across 2 levels with different sections:
        - Level 1: Regular (15 slots), VIP (10 slots), EV (6 slots) per vehicle type
        - Level 2: Regular (15 slots), VIP (10 slots), EV (6 slots) per vehicle type
        Total: 186 slots (31 per vehicle type × 3 types × 2 levels)
        """
        self.slots = {}
        self.lock = threading.RLock()  # Use RLock for reentrant locking
        self.vip_passes = {}  # license_plate -> expiry_datetime for VIP monthly passes

        # Create slots for each level and section
        slot_id = 1
        for level in [1, 2]:
            # Regular section: 15 slots per vehicle type
            for vehicle_type in VehicleType:
                for i in range(15):
                    slot = Slot(f"R{level}{vehicle_type.value[0]}{i+1:02d}", level, Section.REGULAR, vehicle_type)
                    self.slots[slot.id] = slot

            # VIP section: 10 slots per vehicle type
            for vehicle_type in VehicleType:
                for i in range(10):
                    slot = Slot(f"V{level}{vehicle_type.value[0]}{i+1:02d}", level, Section.VIP, vehicle_type)
                    self.slots[slot.id] = slot

            # EV section: 6 slots per vehicle type (for electric vehicles)
            for vehicle_type in VehicleType:
                for i in range(6):
                    slot = Slot(f"E{level}{vehicle_type.value[0]}{i+1:02d}", level, Section.EV, vehicle_type)
                    self.slots[slot.id] = slot

    def find_slot(self, vehicle_type, customer_type, is_ev=False):
        """
        Find an available slot for the given vehicle and customer type.

        Priority rules:
        1. EV vehicles get priority in EV sections
        2. VIP customers get priority in VIP sections
        3. Regular customers use regular sections
        4. If preferred section full, use other sections

        Args:
            vehicle_type (VehicleType): Type of vehicle
            customer_type (CustomerType): Type of customer
            is_ev (bool): Whether this is an electric vehicle

        Returns:
            Slot: Available slot or None if no slots available
        """
        with self.lock:
            # Determine preferred sections based on customer and vehicle type
            preferred_sections = []
            fallback_sections = []

            if is_ev:
                # EV vehicles prefer EV section first
                preferred_sections = [Section.EV]
                if customer_type == CustomerType.VIP:
                    fallback_sections = [Section.VIP, Section.REGULAR]
                else:
                    fallback_sections = [Section.REGULAR, Section.VIP]
            elif customer_type == CustomerType.VIP:
                # VIP customers prefer VIP section
                preferred_sections = [Section.VIP]
                fallback_sections = [Section.REGULAR, Section.EV]
            else:
                # Regular customers prefer regular section
                preferred_sections = [Section.REGULAR]
                fallback_sections = [Section.EV, Section.VIP]

            # Search in preferred sections first
            for section in preferred_sections:
                slot = self._find_slot_in_section(vehicle_type, section)
                if slot:
                    return slot

            # If no slot in preferred sections, try fallback sections
            for section in fallback_sections:
                slot = self._find_slot_in_section(vehicle_type, section)
                if slot:
                    return slot

            return None

    def _find_slot_in_section(self, vehicle_type, section):
        """
        Find an available slot in a specific section for the given vehicle type.

        Args:
            vehicle_type (VehicleType): Type of vehicle
            section (Section): Section to search in

        Returns:
            Slot: Available slot or None
        """
        # Get all slots in the section that match the vehicle type
        section_slots = [slot for slot in self.slots.values()
                        if slot.section == section and slot.vehicle_type == vehicle_type and not slot.is_occupied]

        if not section_slots:
            return None        # For VIP sections, prefer lower level first
        if section == Section.VIP:
            section_slots.sort(key=lambda s: s.level)

        # For regular sections, prefer lower level first
        elif section == Section.REGULAR:
            section_slots.sort(key=lambda s: s.level)

        # For EV sections, prefer lower level first
        else:  # Section.EV
            section_slots.sort(key=lambda s: s.level)

        return section_slots[0] if section_slots else None

    def allocate_slot(self, vehicle, is_ev=False):
        """
        Allocate a slot for the given vehicle.

        Args:
            vehicle (Vehicle): Vehicle to park
            is_ev (bool): Whether this is an electric vehicle

        Returns:
            Slot: Allocated slot or None if no slots available
        """
        with self.lock:
            slot = self.find_slot(vehicle.vehicle_type, vehicle.customer_type, is_ev)
            if slot and slot.allocate(vehicle):
                return slot
            return None

    def release_slot(self, ticket_id):
        """
        Release a slot by ticket ID.

        Args:
            ticket_id (str): Ticket ID of the vehicle to release

        Returns:
            Slot: Released slot or None if ticket not found
        """
        with self.lock:
            for slot in self.slots.values():
                if slot.is_occupied and slot.vehicle.ticket_id == ticket_id:
                    vehicle = slot.release()
                    return slot
            return None

    def get_slot_by_ticket(self, ticket_id):
        """
        Get slot information by ticket ID.

        Args:
            ticket_id (str): Ticket ID

        Returns:
            Slot: Slot with the ticket or None
        """
        with self.lock:
            for slot in self.slots.values():
                if slot.is_occupied and slot.vehicle.ticket_id == ticket_id:
                    return slot
            return None

    def get_all_slots(self):
        """
        Get all slots in the parking lot.

        Returns:
            list: List of all Slot objects
        """
        with self.lock:
            return list(self.slots.values())

    def get_occupied_slots(self):
        """
        Get all occupied slots.

        Returns:
            list: List of occupied Slot objects
        """
        with self.lock:
            return [slot for slot in self.slots.values() if slot.is_occupied]

    def get_available_slots_count(self):
        """
        Get count of available slots by type and section.

        Returns:
            dict: Dictionary with counts by vehicle type and section
        """
        with self.lock:
            counts = {}
            for vehicle_type in VehicleType:
                counts[vehicle_type.value] = {}
                for section in Section:
                    count = len([slot for slot in self.slots.values()
                               if slot.vehicle_type == vehicle_type and slot.section == section and not slot.is_occupied])
                    counts[vehicle_type.value][section.value] = count
            return counts

    def check_expired_slots(self):
        """
        Check for expired slots and return them.

        Returns:
            list: List of expired Slot objects
        """
        with self.lock:
            return [slot for slot in self.slots.values() if slot.is_expired()]

    def check_peak_hour_restrictions(self, vehicle_type):
        """
        Check if vehicle type is restricted during peak hours.

        Args:
            vehicle_type (VehicleType): Type of vehicle

        Returns:
            bool: True if restricted, False otherwise
        """
        if not ParkingRules.RESTRICTIONS['commercial_vehicle_restrictions']:
            return False

        now = datetime.now()
        current_time = now.strftime('%H:%M')

        for peak_period in ParkingRules.RESTRICTIONS['peak_hours']:
            start, end = peak_period.split('-')
            if start <= current_time <= end and vehicle_type == VehicleType.LARGE:
                return True

        return False

    def validate_vehicle_entry(self, vehicle, is_ev=False):
        """
        Validate if a vehicle can enter based on current policies.

        Args:
            vehicle (Vehicle): Vehicle attempting to enter
            is_ev (bool): Whether this is an electric vehicle

        Returns:
            tuple: (can_enter: bool, reason: str)
        """
        with self.lock:
            # Check if suspended
            if vehicle.is_suspended:
                return False, f"Vehicle suspended: {vehicle.suspension_reason}"

            # Check peak hour restrictions
            if self.check_peak_hour_restrictions(vehicle.vehicle_type):
                return False, "Large vehicles restricted during peak hours"

            # Check re-entry rules
            if not vehicle.can_re_enter():
                return False, "Maximum re-entries exceeded"

            # Check if vehicle already parked (only for regular customers - VIP allows multiple parking)
            if vehicle.customer_type == CustomerType.REGULAR:
                for slot in self.slots.values():
                    if (slot.is_occupied and
                        slot.vehicle.license_plate == vehicle.license_plate):
                        return False, "Vehicle already parked"

            return True, "Entry allowed"

    def process_vehicle_exit(self, ticket_id):
        """
        Process vehicle exit with policy enforcement.

        Args:
            ticket_id (str): Ticket ID of exiting vehicle

        Returns:
            dict: Exit processing result with fees and warnings
        """
        with self.lock:
            slot = self.get_slot_by_ticket(ticket_id)
            if not slot:
                return {'success': False, 'reason': 'Ticket not found'}

            vehicle = slot.vehicle
            fee = slot.calculate_fee()
            re_entry_fee = vehicle.get_re_entry_fee()
            total_fee = fee + re_entry_fee

            # Check for overstay
            is_overstay = slot.is_expired()
            if is_overstay:
                vehicle.issue_warning("Overstay violation")

            # Record parking session
            exit_time = datetime.now()
            vehicle.add_parking_session(slot.allocation_time, exit_time, slot.id)
            vehicle.total_fees_paid += total_fee

            # Release slot
            released_slot = self.release_slot(ticket_id)

            result = {
                'success': True,
                'vehicle': vehicle,
                'slot': released_slot,
                'base_fee': fee,
                're_entry_fee': re_entry_fee,
                'total_fee': total_fee,
                'overstay': is_overstay,
                'warnings': vehicle.warnings_issued,
                'exit_time': exit_time
            }

            return result

    def get_system_status(self):
        """
        Get comprehensive system status including policy information.

        Returns:
            dict: System status with counts, policies, and operational info
        """
        with self.lock:
            occupied_slots = self.get_occupied_slots()
            available_counts = self.get_available_slots_count()
            expired_slots = self.check_expired_slots()

            return {
                'total_slots': len(self.slots),
                'occupied_slots': len(occupied_slots),
                'available_slots': len(self.slots) - len(occupied_slots),
                'expired_slots': len(expired_slots),
                'available_counts': available_counts,
                'rules': ParkingRules.get_rules_text(),
                'timestamp': datetime.now()
            }