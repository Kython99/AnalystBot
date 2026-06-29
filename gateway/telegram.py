"""
Telegram gateway — webhook handler for incoming messages.
Runs as a FastAPI route, not a long-polling bot.
"""
import os
import re
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from core.agent_loop import AgentLoop
from tenants.registry import TenantRegistry
from gateway.onboarding import OnboardingFlow

router = APIRouter()

TELEGRAM_API = "https://api.telegram.org"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_IP = os.getenv("ALLOWED_IPS", "").split(",")
ALLOWED_IP = [ip.strip() for ip in ALLOWED_IP if ip.strip()]

# Verify IP whitelist
def _check_ip(request: Request):
    """Reject requests not from allowed IPs."""
    if not ALLOWED_IP:
        return  # No restriction configured

    client_ip = request.client.host if request.client else None
    if client_ip not in ALLOWED_IP:
        raise HTTPException(status_code=403, detail="Forbidden")


agent_loop = AgentLoop()
registry = TenantRegistry()
onboarding = OnboardingFlow()


def _send_telegram(method: str, data: dict) -> dict:
    """Make a call to the Telegram Bot API."""
    url = f"{TELEGRAM_API}/bot{TELEGRAM_BOT_TOKEN}/{method}"
    with httpx.Client() as client:
        resp = client.post(url, json=data, timeout=10)
    return resp.json()


def _send_message(chat_id: int, text: str, reply_to: int = None):
    """Send a text message back to the user."""
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_to:
        data["reply_to_message_id"] = reply_to
    return _send_telegram("sendMessage", data)


@router.post(f"/webhook/{TELEGRAM_BOT_TOKEN}")
async def webhook(request: Request):
    """
    Main Telegram webhook endpoint.
    Receives messages, routes to onboarding or the agent.
    """
    # IP check
    _check_ip(request)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False}, status_code=400)

    # Handle edited messages too
    edited_message = body.get("edited_message", {})
    if edited_message:
        return JSONResponse({"ok": True})  # We don't handle edits yet

    message = body.get("message", {})
    if not message:
        return JSONResponse({"ok": True})

    chat_id = str(message.get("chat", {}).get("id", ""))
    message_id = message.get("message_id")

    if not chat_id:
        return JSONResponse({"ok": True})

    # Check for document (file upload)
    document = message.get("document")
    if document:
        await _handle_document(chat_id, document, message_id)
        return JSONResponse({"ok": True})

    text = message.get("text", "").strip()
    if not text:
        return JSONResponse({"ok": True})

    # Check if this is a command
    if text.startswith("/"):
        await _handle_command(chat_id, text, message_id)
    else:
        await _handle_message(chat_id, text, message_id)

    return JSONResponse({"ok": True})


async def _handle_command(chat_id: str, text: str, message_id: int):
    """Handle /commands."""
    cmd = text.split()[0].lower()

    if cmd == "/start":
        await onboarding.start(chat_id, message_id, _send_message)
    elif cmd == "/help":
        await _send_message(int(chat_id), "📊 <b>AnalystBot Commands</b>\n\n/start — Start or restart setup\n/help — Show this message\n/summary — Generate a sales report\n/myuploads — List your uploaded files\n/usage — Check your usage\n/reset — Reset conversation history", message_id)
    elif cmd == "/summary":
        result = agent_loop.process(chat_id, "Generate a full sales summary and recommendations for my data.")
        await _send_message(int(chat_id), result, message_id)
    elif cmd == "/myuploads":
        from tools.excel import list_files
        result = list_files(chat_id)
        await _send_message(int(chat_id), result, message_id)
    elif cmd == "/usage":
        usage = registry.ctx.get_usage(chat_id)
        used = usage.get("prompts_used", 0)
        limit = usage.get("limit", 500)
        remaining = max(0, limit - used)
        await _send_message(int(chat_id), f"📊 <b>Usage</b>\n\nUsed: {used} / {limit}\nRemaining: {remaining}", message_id)
    elif cmd == "/reset":
        registry.ctx.save_history(chat_id, [])
        await _send_message(int(chat_id), "🔄 Conversation history cleared.", message_id)
    else:
        await _send_message(int(chat_id), f"Unknown command: {cmd}. Type /help for available commands.", message_id)


async def _handle_message(chat_id: str, text: str, message_id: int):
    """Handle regular text messages."""
    # Check if tenant is onboarded
    config = registry.ctx.get_config(chat_id)

    if not config.get("data_sources"):
        # Not onboarded — run onboarding
        await onboarding.continue_flow(chat_id, text, message_id, _send_message)
        return

    # Run the agent
    result = agent_loop.process(chat_id, text)
    await _send_message(int(chat_id), result, message_id)


async def _handle_document(chat_id: str, document: dict, message_id: int):
    """Handle a file upload via Telegram document."""
    file_id = document.get("file_id")
    filename = document.get("file_name", "uploaded_file")
    mime_type = document.get("mime_type", "")

    # Validate file type
    allowed_mimes = {"text/csv": ".csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
                     "application/vnd.ms-excel": ".xls"}
    ext = allowed_mimes.get(mime_type)
    if not ext:
        await _send_message(int(chat_id),
            "❌ Unsupported file type. Please upload a CSV or Excel (.xlsx/.xls) file.",
            message_id)
        return

    # Ensure filename has correct extension
    if not filename.endswith(ext):
        filename += ext

    # Download file from Telegram
    try:
        file_content = await _download_telegram_file(file_id)
    except Exception as e:
        await _send_message(int(chat_id), f"❌ Failed to download file: {e}", message_id)
        return

    # Save to tenant uploads
    try:
        path = registry.ctx.upload_file(chat_id, filename, file_content)
        # Update config
        config = registry.ctx.get_config(chat_id)
        sources = config.get("data_sources", [])
        sources.append({"type": "file", "filename": filename, "label": filename})
        config["data_sources"] = sources
        registry.ctx.save_config(chat_id, config)

        await _send_message(int(chat_id),
            f"✅ File '{filename}' saved! I'll analyse it now.",
            message_id)

        # Auto-analyse the file
        from tools.excel import read_csv, read_excel
        if filename.endswith(".csv"):
            data = read_csv(chat_id, filename)
        else:
            data = read_excel(chat_id, filename)

        result = agent_loop.process(chat_id,
            f"Analyse this data and give me a sales summary:\n\n{data[:3000]}")
        await _send_message(int(chat_id), result)

    except Exception as e:
        await _send_message(int(chat_id), f"❌ Error saving file: {e}", message_id)


async def _download_telegram_file(file_id: str) -> bytes:
    """Download a file from Telegram using the bot token."""
    # Get file path
    get_url = f"{TELEGRAM_API}/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
    with httpx.Client() as client:
        resp = client.get(get_url, timeout=10)
    result = resp.json()
    if not result.get("ok"):
        raise Exception(f"Telegram API error: {result}")

    file_path = result["result"]["file_path"]
    download_url = f"{TELEGRAM_API}/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

    with httpx.Client() as client:
        resp = client.get(download_url, timeout=30)
    return resp.content
