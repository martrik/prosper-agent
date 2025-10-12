import random
import re
import string
from datetime import datetime
from typing import Optional

from dateutil import parser as date_parser
from loguru import logger
from pipecat_flows import FlowArgs, FlowManager, FlowResult, FlowsFunctionSchema, NodeConfig


class ClaimNumberResult(FlowResult):
    claim_number: str

class SubmissionDateResult(FlowResult):
    date: str

class StatusResult(FlowResult):
    status: str

class AmountResult(FlowResult):
    amount: str

class VerificationResult(FlowResult):
    confirmed: bool


def generate_claim_number() -> str:
    """Generate 10 alphanumeric characters + 3 zeros (13 total)"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=10)) + '000'


def validate_date(date_str: str) -> tuple[bool, Optional[str]]:
    """
    Validate and parse date from various formats.
    Returns (is_valid, parsed_date_string or error_message)
    """
    if not date_str:
        return False, "No date provided"
    
    try:
        parsed_date = date_parser.parse(date_str, fuzzy=True)
        return True, parsed_date.strftime('%Y-%m-%d')
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse date '{date_str}': {e}")
        return False, f"Could not understand the date '{date_str}'"


def validate_status(status: str) -> tuple[bool, Optional[str]]:
    """
    Validate claim status against common statuses.
    Returns (is_valid, normalized_status or error_message)
    """
    if not status:
        return False, "No status provided"
    
    valid_statuses = [
        "Pending",
        "Approved", 
        "Denied",
        "Rejected",
        "In Review",
        "Under Investigation",
        "Closed",
        "Appealed"
    ]
    
    status_lower = status.lower().strip()
    
    for valid_status in valid_statuses:
        if status_lower in valid_status.lower() or valid_status.lower() in status_lower:
            return True, valid_status
    
    return False, f"Status '{status}' is not recognized. Valid statuses are: {', '.join(valid_statuses)}"


def validate_amount(amount_str: str) -> tuple[bool, Optional[str]]:
    """
    Validate and parse claim amount.
    Returns (is_valid, formatted_amount or error_message)
    """
    if not amount_str:
        return False, "No amount provided"
    
    cleaned = amount_str.strip().replace('$', '').replace(',', '').replace(' ', '')
    
    try:
        amount = float(cleaned)
        if amount <= 0:
            return False, "Claim amount must be greater than zero"
        return True, f"${amount:,.2f}"
    except ValueError:
        logger.warning(f"Failed to parse amount '{amount_str}'")
        return False, f"Could not understand the amount '{amount_str}'. Please provide a number"


async def handle_greeting(args: FlowArgs, flow_manager: FlowManager) -> tuple[ClaimNumberResult, NodeConfig]:
    """Handle initial greeting from user and provide claim number"""
    claim_number = generate_claim_number()
    flow_manager.state["claim_number"] = claim_number
    
    logger.info(f"Generated claim number: {claim_number}")
    
    return ClaimNumberResult(claim_number=claim_number), provide_claim_number_node(claim_number)


async def handle_claim_number_acknowledged(args: FlowArgs, flow_manager: FlowManager) -> tuple[FlowResult, NodeConfig]:
    """Handle user acknowledging they found the claim"""
    return FlowResult(), ask_submission_date_node()


async def handle_submission_date(args: FlowArgs, flow_manager: FlowManager) -> tuple[SubmissionDateResult | FlowResult, NodeConfig]:
    """Validate and store submission date"""
    date_input = args.get("date", "")
    
    is_valid, result = validate_date(date_input)
    
    if is_valid:
        flow_manager.state["submission_date"] = result
        logger.info(f"Captured submission date: {result}")
        # TODO: Save to database - claim_data = {"claim_number": flow_manager.state["claim_number"], "submission_date": result}
        return SubmissionDateResult(date=result), ask_status_node()
    else:
        error_msg = f"I'm sorry, {result}. Could you please provide the date again? For example, you can say January 15th 2024, or 01/15/2024."
        return FlowResult(error=error_msg), ask_submission_date_node()


async def handle_status(args: FlowArgs, flow_manager: FlowManager) -> tuple[StatusResult | FlowResult, NodeConfig]:
    """Validate and store claim status"""
    status_input = args.get("status", "")
    
    is_valid, result = validate_status(status_input)
    
    if is_valid:
        flow_manager.state["status"] = result
        logger.info(f"Captured status: {result}")
        # TODO: Save to database - claim_data = {"claim_number": flow_manager.state["claim_number"], "status": result}
        return StatusResult(status=result), ask_amount_node()
    else:
        error_msg = f"I'm sorry, {result}. Please provide one of these statuses."
        return FlowResult(error=error_msg), ask_status_node()


async def handle_amount(args: FlowArgs, flow_manager: FlowManager) -> tuple[AmountResult | FlowResult, NodeConfig]:
    """Validate and store claim amount"""
    amount_input = args.get("amount", "")
    
    is_valid, amount = validate_amount(amount_input)
    
    if is_valid:
        flow_manager.state["amount"] = amount
        logger.info(f"Captured amount: {amount}")
        # TODO: Save to database - claim_data = {"claim_number": flow_manager.state["claim_number"], "amount": amount}
        
        return AmountResult(amount=amount), verify_information_node(
            flow_manager.state["claim_number"],
            flow_manager.state["submission_date"],
            flow_manager.state["status"],
            amount
        )
    else:
        error_msg = f"I'm sorry, {amount}. Please provide the claim amount as a number."
        return FlowResult(error=error_msg), ask_amount_node()


async def handle_verification(args: FlowArgs, flow_manager: FlowManager) -> tuple[VerificationResult, NodeConfig]:
    """Handle user confirmation of information"""
    confirmed = args.get("confirmed", False)
    
    if confirmed or str(confirmed).lower() in ["yes", "true", "correct", "right", "yep", "yeah"]:
        logger.info("User confirmed all information is correct")
        # TODO: Save final confirmation to database
        return VerificationResult(confirmed=True), end_node()
    else:
        logger.info("User wants to make corrections")
        return VerificationResult(confirmed=False), correction_node()


async def handle_correction(args: FlowArgs, flow_manager: FlowManager) -> tuple[FlowResult, NodeConfig]:
    """Route to appropriate node based on what needs correction"""
    field_to_correct = args.get("field_to_correct", "").lower()
    
    logger.info(f"User wants to correct: {field_to_correct}")
    
    if "date" in field_to_correct or "submit" in field_to_correct:
        return FlowResult(), ask_submission_date_node()
    elif "status" in field_to_correct:
        return FlowResult(), ask_status_node()
    elif "amount" in field_to_correct or "money" in field_to_correct or "dollar" in field_to_correct:
        return FlowResult(), ask_amount_node()
    else:
        return FlowResult(error="I didn't catch which field you'd like to correct. Please specify the submission date, status, or amount."), correction_node()


def start_node():
    """Initial node - bot initiates conversation"""
    return NodeConfig(
        role_messages=[
            {
                "role": "system",
                "content": "You are a professional caller inquiring about claim information. Keep your responses natural and conversational. Your output will be converted to audio so don't include special characters."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": "Greet the user and say you need information about a claim. Wait for them to ask which claim or for the claim number."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="provide_claim_number",
                description="Called when the user asks for the claim number or says they can help.",
                handler=handle_greeting,
                properties={},
                required=[]
            )
        ]
    )


def provide_claim_number_node(claim_number: str):
    """Provide the generated claim number"""
    return NodeConfig(
        task_messages=[
            {
                "role": "system", 
                "content": f"Tell the user the claim number is {claim_number}. Speak it clearly, character by character or in groups. Wait for them to confirm they found it in their system."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="claim_found",
                description="Called when the user confirms they found the claim and asks what you need.",
                handler=handle_claim_number_acknowledged,
                properties={},
                required=[]
            )
        ]
    )


def ask_submission_date_node():
    """Ask for claim submission date"""
    return NodeConfig(
        task_messages=[
            {
                "role": "system",
                "content": "Ask when the claim was submitted. Be natural and conversational."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="capture_submission_date",
                description="Capture the date when the claim was submitted",
                handler=handle_submission_date,
                properties={
                    "date": {
                        "type": "string",
                        "description": "The date when the claim was submitted, in any common date format"
                    }
                },
                required=["date"]
            )
        ]
    )


def ask_status_node():
    """Ask for claim status"""
    return NodeConfig(
        task_messages=[
            {
                "role": "system",
                "content": "Ask what the current status of the claim is. Be natural and conversational."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="capture_status",
                description="Capture the current status of the claim",
                handler=handle_status,
                properties={
                    "status": {
                        "type": "string",
                        "description": "The current status of the claim (e.g., Pending, Approved, Denied, In Review, etc.)"
                    }
                },
                required=["status"]
            )
        ]
    )


def ask_amount_node():
    """Ask for claim amount"""
    return NodeConfig(
        task_messages=[
            {
                "role": "system",
                "content": "Ask what the claim amount is. Be natural and conversational."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="capture_amount",
                description="Capture the claim amount",
                handler=handle_amount,
                properties={
                    "amount": {
                        "type": "string",
                        "description": "The claim amount, which can include dollar signs, commas, or be written as a number"
                    }
                },
                required=["amount"]
            )
        ]
    )


def verify_information_node(claim_number: str, submission_date: str, status: str, amount: str):
    """Verify all collected information with the user"""
    return NodeConfig(
        task_messages=[
            {
                "role": "system",
                "content": f"Read back all the information you've collected: the claim number is {claim_number}, the submission date is {submission_date}, the status is {status}, and the claim amount is {amount}. Then ask if this is all correct."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="verify_information",
                description="Called when user confirms or denies the information is correct",
                handler=handle_verification,
                properties={
                    "confirmed": {
                        "type": "boolean",
                        "description": "True if user confirms information is correct, False if they want to make corrections"
                    }
                },
                required=["confirmed"]
            )
        ]
    )


def correction_node():
    """Ask which field needs correction"""
    return NodeConfig(
        task_messages=[
            {
                "role": "system",
                "content": "Ask which piece of information they would like to correct: the submission date, status, or claim amount."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="identify_correction",
                description="Identify which field the user wants to correct",
                handler=handle_correction,
                properties={
                    "field_to_correct": {
                        "type": "string",
                        "enum": ["date", "status", "amount"],
                        "description": "The field that needs to be corrected"
                    }
                },
                required=["field_to_correct"]
            )
        ]
    )


def end_node():
    """End the conversation"""
    return NodeConfig(
        task_messages=[
            {
                "role": "system",
                "content": "Thank the user for providing the information and wish them a great day. Keep it brief and professional."
            }
        ],
        functions=[]
    )


initial_node = start_node()

