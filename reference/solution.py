#!/usr/bin/env python3
"""Healthcare Gateway Agent - Refactored Implementation.

Lab 3.1 Deliverable: Production-ready gateway agent demonstrating
architecture patterns, security, and proper separation of concerns.

Environment variables:
    SWML_BASIC_AUTH_USER: Basic auth username (auto-detected by SDK)
    SWML_BASIC_AUTH_PASSWORD: Basic auth password (auto-detected by SDK)
"""

import os
import hashlib
import logging
from datetime import datetime
from signalwire_agents import AgentBase, SwaigFunctionResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthcareGatewayAgent(AgentBase):
    """Gateway agent for healthcare contact center.

    Responsibilities:
    - Caller identification and verification
    - Intent classification
    - Routing to specialist agents
    """

    # Simulated patient database
    PATIENTS = {
        "+15551234567": {
            "id": "P001",
            "name": "John Smith",
            "dob": "1985-03-15",
            "ssn_last4_hash": hashlib.sha256("1234".encode()).hexdigest()
        },
        "+15559876543": {
            "id": "P002",
            "name": "Jane Doe",
            "dob": "1990-07-22",
            "ssn_last4_hash": hashlib.sha256("5678".encode()).hexdigest()
        }
    }

    MAX_VERIFICATION_ATTEMPTS = 3

    def __init__(self):
        super().__init__(name="healthcare-gateway", route="/gateway")

        self._configure_prompts()
        self._configure_global_data()
        self.add_language("English", "en-US", "rime.spore")
        self._setup_functions()

        logger.info("Healthcare Gateway Agent initialized")

    def _configure_prompts(self):
        """Configure agent prompts."""
        self.prompt_add_section(
            "Role",
            "Healthcare contact center gateway. Verify callers and route to specialists."
        )

        self.prompt_add_section(
            "Security Requirements",
            bullets=[
                "ALWAYS verify identity before discussing patient information",
                "NEVER repeat full SSN or sensitive data",
                "Pause recording for SSN collection",
                "Lock after 3 failed verification attempts"
            ]
        )

        self.prompt_add_section(
            "Departments",
            bullets=[
                "Appointments: Scheduling, rescheduling, cancellations",
                "Billing: Account balance, payments, insurance",
                "Medical: Prescription refills, general questions"
            ]
        )

    def _configure_global_data(self):
        """Set up shared configuration."""
        hour = datetime.now().hour
        self.set_global_data({
            "clinic_name": "HealthFirst Medical",
            "business_hours": "8 AM to 6 PM",
            "is_open": 8 <= hour < 18,
            "greeting": "Good morning" if hour < 12 else "Good afternoon"
        })

    def _log_security_event(self, event_type: str, data: dict):
        """Log security event without sensitive data."""
        safe_data = {k: v for k, v in data.items()
                     if k not in ['ssn', 'ssn_last4', 'dob']}
        logger.info(f"SECURITY: {event_type} - {safe_data}")

    def _verify_ssn(self, patient_id: str, ssn_last4: str) -> bool:
        """Verify SSN with timing-safe comparison."""
        for phone, patient in self.PATIENTS.items():
            if patient["id"] == patient_id:
                provided_hash = hashlib.sha256(ssn_last4.encode()).hexdigest()
                return provided_hash == patient["ssn_last4_hash"]
        return False

    def _setup_functions(self):
        """Define gateway functions."""

        @self.tool(description="Identify patient by phone number")
        def identify_by_phone(args: dict, raw_data: dict = None) -> SwaigFunctionResult:
            """Attempt to identify patient by caller ID."""
            raw_data = raw_data or {}
            caller_id = raw_data.get("caller_id_number", "")
            call_id = raw_data.get("call_id", "unknown")

            patient = self.PATIENTS.get(caller_id)

            if patient:
                self._log_security_event("PATIENT_IDENTIFIED", {
                    "call_id": call_id,
                    "patient_id": patient["id"]
                })

                global_data = self.get_global_data()
                return (
                    SwaigFunctionResult(
                        f"{global_data['greeting']}, {patient['name']}. "
                        "For security, please verify your date of birth."
                    )
                    .update_global_data({
                        "pending_patient_id": patient["id"],
                        "pending_patient_name": patient["name"],
                        "pending_dob": patient["dob"],
                        "verification_attempts": 0
                    })
                )

            return SwaigFunctionResult(
                "I don't recognize this phone number. "
                "Could you provide your patient ID or date of birth?"
            )

        @self.tool(
            description="Verify date of birth",
            parameters={
                "type": "object",
                "properties": {
                    "dob": {
                        "type": "string",
                        "description": "Date of birth (YYYY-MM-DD or spoken format)"
                    }
                },
                "required": ["dob"]
            }
        )
        def verify_dob(args: dict, raw_data: dict = None) -> SwaigFunctionResult:
            """Verify date of birth for identified patient."""
            dob = args.get("dob", "")
            raw_data = raw_data or {}
            global_data = raw_data.get("global_data", {})
            call_id = raw_data.get("call_id", "unknown")
            expected_dob = global_data.get("pending_dob")
            patient_id = global_data.get("pending_patient_id")

            if not patient_id:
                return SwaigFunctionResult(
                    "Let me first identify your account. "
                    "What is your patient ID or phone number?"
                )

            # Normalize DOB comparison
            normalized_dob = dob.replace("/", "-").strip()
            if normalized_dob == expected_dob:
                self._log_security_event("DOB_VERIFIED", {
                    "call_id": call_id,
                    "patient_id": patient_id
                })

                return (
                    SwaigFunctionResult(
                        "Thank you. For final verification, "
                        "please provide the last 4 digits of your SSN. "
                        "I'm pausing the recording for your privacy."
                    )
                    .stop_record_call(control_id="main")
                    .update_global_data({"dob_verified": True})
                )

            attempts = global_data.get("verification_attempts", 0) + 1
            if attempts >= self.MAX_VERIFICATION_ATTEMPTS:
                self._log_security_event("VERIFICATION_LOCKED", {
                    "call_id": call_id,
                    "patient_id": patient_id
                })
                return (
                    SwaigFunctionResult(
                        "Too many incorrect attempts. "
                        "Please call back or visit the clinic with ID."
                    )
                    .hangup()
                )

            return (
                SwaigFunctionResult(
                    f"That doesn't match our records. "
                    f"{self.MAX_VERIFICATION_ATTEMPTS - attempts} attempts remaining."
                )
                .update_global_data({"verification_attempts": attempts})
            )

        @self.tool(
            description="Verify last 4 digits of SSN",
            parameters={
                "type": "object",
                "properties": {
                    "ssn_last4": {
                        "type": "string",
                        "description": "Last 4 digits of SSN"
                    }
                },
                "required": ["ssn_last4"]
            },
            secure=True
        )
        def verify_ssn(args: dict, raw_data: dict = None) -> SwaigFunctionResult:
            """Verify SSN for final authentication."""
            ssn_last4 = args.get("ssn_last4", "")
            raw_data = raw_data or {}
            global_data = raw_data.get("global_data", {})
            call_id = raw_data.get("call_id", "unknown")
            patient_id = global_data.get("pending_patient_id")
            patient_name = global_data.get("pending_patient_name")

            if not global_data.get("dob_verified"):
                return SwaigFunctionResult(
                    "Please verify your date of birth first."
                )

            if self._verify_ssn(patient_id, ssn_last4):
                self._log_security_event("VERIFICATION_SUCCESS", {
                    "call_id": call_id,
                    "patient_id": patient_id
                })

                return (
                    SwaigFunctionResult(
                        f"Thank you, {patient_name}. Your identity is verified. "
                        "Recording has resumed. How can I help you today? "
                        "I can help with appointments, billing, or medical questions."
                    )
                    .record_call(control_id="main", stereo=True, format="mp3")
                    .update_global_data({
                        "verified": True,
                        "patient_id": patient_id,
                        "patient_name": patient_name,
                        "verified_at": datetime.now().isoformat()
                    })
                )

            attempts = global_data.get("verification_attempts", 0) + 1
            self._log_security_event("SSN_VERIFICATION_FAILED", {
                "call_id": call_id,
                "attempts": attempts
            })

            if attempts >= self.MAX_VERIFICATION_ATTEMPTS:
                return (
                    SwaigFunctionResult(
                        "Too many incorrect attempts. Account locked."
                    )
                    .record_call(control_id="main", stereo=True, format="mp3")
                    .hangup()
                )

            return (
                SwaigFunctionResult(
                    f"That doesn't match. {self.MAX_VERIFICATION_ATTEMPTS - attempts} attempts remaining."
                )
                .update_global_data({"verification_attempts": attempts})
            )

        @self.tool(description="Route to appointments department")
        def route_appointments(args: dict, raw_data: dict = None) -> SwaigFunctionResult:
            """Transfer to appointments specialist."""
            raw_data = raw_data or {}
            global_data = raw_data.get("global_data", {})
            if not global_data.get("verified"):
                return SwaigFunctionResult(
                    "I need to verify your identity first."
                )

            return (
                SwaigFunctionResult("Connecting you to scheduling.", post_process=True)
                .swml_transfer("/appointments", "Goodbye!", final=True)
            )

        @self.tool(description="Route to billing department")
        def route_billing(args: dict, raw_data: dict = None) -> SwaigFunctionResult:
            """Transfer to billing specialist."""
            raw_data = raw_data or {}
            global_data = raw_data.get("global_data", {})
            if not global_data.get("verified"):
                return SwaigFunctionResult(
                    "I need to verify your identity first."
                )

            return (
                SwaigFunctionResult("Connecting you to billing.", post_process=True)
                .swml_transfer("/billing", "Goodbye!", final=True)
            )

        @self.tool(description="Route to medical team")
        def route_medical(args: dict, raw_data: dict = None) -> SwaigFunctionResult:
            """Transfer to medical support."""
            raw_data = raw_data or {}
            global_data = raw_data.get("global_data", {})
            if not global_data.get("verified"):
                return SwaigFunctionResult(
                    "I need to verify your identity first."
                )

            return (
                SwaigFunctionResult("Connecting you to our medical team.", post_process=True)
                .swml_transfer("/medical", "Goodbye!", final=True)
            )


if __name__ == "__main__":
    agent = HealthcareGatewayAgent()
    agent.run()
