import os
from typing import Optional

from loguru import logger
from supabase import create_client, Client

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)


async def create_conversation_record(claim_number: str) -> Optional[int]:
    """Create a new conversation record in Supabase and return the ID"""
    try:
        response = supabase.table("conversations").insert({
            "claim_id": claim_number,
            "state": "ongoing"
        }).execute()
        
        if response.data and len(response.data) > 0:
            conversation_id = response.data[0]["id"]
            return conversation_id
        return None
    except Exception as e:
        logger.error(f"Failed to create conversation record: {e}")
        return None


async def update_conversation_record(conversation_id: int, data: dict) -> bool:
    """Update an existing conversation record in Supabase"""
    try:
        response = supabase.table("conversations").update(data).eq("id", conversation_id).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to update conversation record: {e}", exc_info=True)
        return False


async def create_conversation_metrics_record(conversation_id: int, metrics_data: dict) -> bool:
    """Create a conversation metrics record in Supabase"""
    try:
        data = {
            "conversation_id": conversation_id,
            **metrics_data
        }
        response = supabase.table("conversation_metrics").insert(data).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to create conversation metrics record: {e}", exc_info=True)
        return False
