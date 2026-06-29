"""
Claude API wrapper for AnalystBot.
"""
import anthropic
import os
from typing import Optional

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1024


def completion(
    system_prompt: str,
    messages: list[dict],
    max_tokens: int = MAX_TOKENS,
    model: str = MODEL,
) -> str:
    """
    Send a completion request to Claude and return the response text.

    Args:
        system_prompt: The system prompt
        messages: List of {"role": "user"|"assistant", "content": str} messages
        max_tokens: Max tokens in response
        model: Model to use

    Returns:
        The assistant's response text
    """
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text
