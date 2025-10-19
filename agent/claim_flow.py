import random
import re
import string
from datetime import datetime
from typing import Optional

from dateutil import parser as date_parser
from loguru import logger
from pipecat_flows import FlowArgs, FlowManager, FlowResult, FlowsFunctionSchema, NodeConfig

from agent.database import create_conversation_record, update_conversation_record


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
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=10)) + '000'


def validate_date(date_str: str) -> tuple[bool, Optional[str]]:
    if not date_str:
        return False, "No date provided"
    
    try:
        parsed_date = date_parser.parse(date_str, fuzzy=True)
        return True, parsed_date.strftime('%Y-%m-%d')
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse date '{date_str}': {e}")
        return False, f"Could not understand the date '{date_str}'"


def validate_status(status: str) -> tuple[bool, Optional[str]]:
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
    claim_number = flow_manager.state.get("claim_number")
    
    if not claim_number:
        claim_number = generate_claim_number()
        flow_manager.state["claim_number"] = claim_number
        
    conversation_id = await create_conversation_record(claim_number)
    if conversation_id:
        flow_manager.state["conversation_id"] = conversation_id
        await update_conversation_record(conversation_id, {"state": "ongoing"})
    
    return ClaimNumberResult(claim_number=claim_number), ask_submission_date_node()


async def handle_submission_date(args: FlowArgs, flow_manager: FlowManager) -> tuple[SubmissionDateResult | FlowResult, NodeConfig]:
    date_input = args.get("date", "")
    
    is_valid, result = validate_date(date_input)
    
    if is_valid:
        flow_manager.state["submission_date"] = result
        logger.info(f"Captured submission date: {result}")
        
        conversation_id = flow_manager.state.get("conversation_id")
        if conversation_id:
            await update_conversation_record(conversation_id, {"claim_date": result})
        
        if flow_manager.state.get("correcting"):
            flow_manager.state["correcting"] = False
            return SubmissionDateResult(date=result), verify_information_node(
                flow_manager.state["claim_number"],
                result,
                flow_manager.state["status"],
                flow_manager.state["amount"]
            )
        
        return SubmissionDateResult(date=result), ask_status_node()
    else:
        error_msg = f"I'm sorry, {result}. Could you please provide the date again? For example, you can say January 15th 2024, or 01/15/2024."
        return FlowResult(error=error_msg), ask_submission_date_node()


async def handle_status(args: FlowArgs, flow_manager: FlowManager) -> tuple[StatusResult | FlowResult, NodeConfig]:
    status_input = args.get("status", "")
    
    is_valid, result = validate_status(status_input)
    
    if is_valid:
        flow_manager.state["status"] = result
        logger.info(f"Captured status: {result}")
        
        conversation_id = flow_manager.state.get("conversation_id")
        if conversation_id:
            await update_conversation_record(conversation_id, {"claim_status": result})
        
        if flow_manager.state.get("correcting"):
            flow_manager.state["correcting"] = False
            return StatusResult(status=result), verify_information_node(
                flow_manager.state["claim_number"],
                flow_manager.state["submission_date"],
                result,
                flow_manager.state["amount"]
            )
        
        return StatusResult(status=result), ask_amount_node()
    else:
        error_msg = f"I'm sorry, {result}. Please provide one of these statuses."
        return FlowResult(error=error_msg), ask_status_node()


async def handle_amount(args: FlowArgs, flow_manager: FlowManager) -> tuple[AmountResult | FlowResult, NodeConfig]:
    amount_input = args.get("amount", "")
    
    is_valid, amount = validate_amount(amount_input)
    
    if is_valid:
        flow_manager.state["amount"] = amount
        logger.info(f"Captured amount: {amount}")
        
        conversation_id = flow_manager.state.get("conversation_id")
        if conversation_id:
            numeric_amount = float(amount.replace('$', '').replace(',', ''))
            await update_conversation_record(conversation_id, {"claim_amount": numeric_amount})
        
        if flow_manager.state.get("correcting"):
            flow_manager.state["correcting"] = False
        
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
    confirmed = args.get("confirmed", False)
    
    if confirmed or str(confirmed).lower() in ["yes", "true", "correct", "right", "yep", "yeah"]:
        logger.info("User confirmed all information is correct")
        
        conversation_id = flow_manager.state.get("conversation_id")
        if conversation_id:
            await update_conversation_record(conversation_id, {"state": "done"})
            logger.info(f"Conversation {conversation_id} completed and verified (state: done)")
        
        return VerificationResult(confirmed=True), end_node()
    else:
        logger.info("User wants to make corrections")
        return VerificationResult(confirmed=False), correction_node()


async def handle_correction(args: FlowArgs, flow_manager: FlowManager) -> tuple[FlowResult, NodeConfig]:
    field_to_correct = args.get("field_to_correct", "").lower()
    
    logger.info(f"User wants to correct: {field_to_correct}")
    
    flow_manager.state["correcting"] = True
    
    if "date" in field_to_correct or "submit" in field_to_correct:
        return FlowResult(), ask_submission_date_node()
    elif "status" in field_to_correct:
        return FlowResult(), ask_status_node()
    elif "amount" in field_to_correct or "money" in field_to_correct or "dollar" in field_to_correct:
        return FlowResult(), ask_amount_node()
    else:
        return FlowResult(error="I didn't catch which field you'd like to correct. Please specify the submission date, status, or amount."), correction_node()


def start_node(claim_number: str):
    return NodeConfig(
        role_messages=[
            {
                "role": "system",
                "content": "You are a professional caller inquiring about claim information. \
                    Keep your responses natural and conversational. \
                    Your output will be converted to audio so don't include special characters."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": f"Introduce yourself and say you need information about a specific claim. \
                    Tell them you're calling about claim number {claim_number}. Speak the claim number clearly, \
                    character by character or in groups, but don't spell it out. Ask them to confirm when they've pulled it up in their system."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="claim_found_in_system",
                description="Called when the user confirms they have found the claim in their system and are ready to provide information about it.",
                handler=handle_greeting,
                properties={},
                required=[]
            )
        ]
    )


def ask_submission_date_node():
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
                        "description": "The claim amount, which can include dollar signs, commas, or be written as a number."
                    }
                },
                required=["amount"]
            )
        ]
    )


def verify_information_node(claim_number: str, submission_date: str, status: str, amount: str):
    return NodeConfig(
        task_messages=[
            {
                "role": "system",
                "content": f"Read back all the information you've collected: the claim number is {claim_number}, \
                    the submission date is {submission_date}, the status is {status}, and the claim amount is {amount}. \
                    When saying the amount, spell it out in words like 'one thousand dollars and zero cents' rather than reading it as digits. \
                    Then ask if this is all correct."
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
    return NodeConfig(
        task_messages=[
            {
                "role": "system",
                "content": "Ask which piece of information they would like to correct: the submission date, status, or amount."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="identify_correction",
                description="Identify which field the user wants to correct (submission date, status, or amount)",
                handler=handle_correction,
                properties={
                    "field_to_correct": {
                        "type": "string",
                        "description": "The field that needs to be corrected - can be variations like 'date', 'submission date', 'status', 'amount', 'claim amount', etc."
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


def create_initial_node():
    claim_number = generate_claim_number()
    return start_node(claim_number)
