#!/usr/bin/env python3
"""Healthcare Gateway Agent - Lab 3.1 Enterprise Architecture.

Demonstrates gateway pattern, caller routing, and proper separation of concerns.
"""

import os
import logging
from signalwire_agents import AgentBase, SwaigFunctionResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GatewayAgent(AgentBase):
    """Gateway agent for healthcare contact center routing."""

    DEPARTMENTS = {
        "member": {
            "route": "/member",
            "description": "Member services - benefits, claims, ID cards"
        },
        "provider": {
            "route": "/provider",
            "description": "Provider services - eligibility, prior authorization"
        },
        "appointments": {
            "route": "/appointments",
            "description": "Scheduling, rescheduling, cancellations"
        },
        "billing": {
            "route": "/billing",
            "description": "Account balance, payments, insurance"
        }
    }

    def __init__(self):
        super().__init__(name="healthcare-gateway", route="/gateway")

        self._configure_prompts()
        self.add_language("English", "en-US", "rime.spore")
        self._setup_functions()

        logger.info("Gateway Agent initialized")

    def _configure_prompts(self):
        """Configure agent prompts."""
        self.prompt_add_section(
            "Role",
            "Healthcare contact center gateway. Route callers to the right department."
        )

        self.prompt_add_section(
            "Departments",
            bullets=[
                "Member services: benefits, claims, ID cards",
                "Provider services: eligibility, prior authorization",
                "Appointments: scheduling, rescheduling, cancellations",
                "Billing: account balance, payments, insurance"
            ]
        )

        self.prompt_add_section(
            "Guidelines",
            bullets=[
                "Identify caller intent quickly",
                "Route to appropriate department",
                "Provide general information for simple inquiries"
            ]
        )

    def _setup_functions(self):
        """Define gateway functions."""

        @self.tool(description="List available departments")
        def list_departments(args: dict = None, raw_data: dict = None) -> SwaigFunctionResult:
            dept_info = [
                f"{name}: {info['description']}"
                for name, info in self.DEPARTMENTS.items()
            ]
            return SwaigFunctionResult(
                "Available departments: " + "; ".join(dept_info)
            )

        @self.tool(
            description="Route call to the appropriate department",
            parameters={
                "type": "object",
                "properties": {
                    "department": {
                        "type": "string",
                        "description": "Department to route to (member, provider, appointments, billing)"
                    }
                },
                "required": ["department"]
            }
        )
        def route_call(args: dict, raw_data: dict = None) -> SwaigFunctionResult:
            department = args.get("department", "").lower()
            dept_info = self.DEPARTMENTS.get(department)

            if not dept_info:
                return SwaigFunctionResult(
                    f"Unknown department '{department}'. "
                    f"Available: {', '.join(self.DEPARTMENTS.keys())}"
                )

            return (
                SwaigFunctionResult(
                    f"Connecting you to {department} services.",
                    post_process=True
                )
                .swml_transfer(dept_info["route"], "Goodbye!", final=True)
            )

        @self.tool(description="Get general information")
        def get_info(args: dict = None, raw_data: dict = None) -> SwaigFunctionResult:
            return SwaigFunctionResult(
                "HealthFirst Medical is open Monday through Friday, 8 AM to 6 PM. "
                "For emergencies, please hang up and call 911. "
                "How can I direct your call today?"
            )


if __name__ == "__main__":
    agent = GatewayAgent()
    agent.run()
