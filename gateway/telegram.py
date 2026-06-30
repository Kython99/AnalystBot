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


def _get_token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


def _get_allowed_ips():
    ips = os.getenv("ALLOWED_IPS", "").split(",")
    return [ip.strip() for ip in ips if ip.strip()]


def _check_ip(request: Request):
    allowed = _get_allowed_ips()
    if not allowed:
        return
    client_ip = request.client.host if request.client else None
    if client_ip not in allowed:
        raise HTTPException(status_code=403, detail="Forbidden")


# Lazy init — avoids loading env vars at import time on serverless
_agent_loop = None
_registry = None
_onboarding = None


def _get_agent_loop():
    global _agent_loop
    if _agent_loop is None:
        _agent_loop = AgentLoop()
    return _agent_loop


def _get_registry():
    global _registry
    if _registry is None:
        _registry = TenantRegistry()
    return _registry


def _get_onboarding():
    global _onboarding
    if _onboarding is None:
        _onboarding = OnboardingFlow()
    return _onboarding


def _send_telegram(method: str, data: dict) -> dict:
    """Make a call to the Telegram Bot API (sync)."""
    token = _get_token()
    url = f"{TELEGRAM_API}/bot{token}/{method}"
    with httpx.Client() as client:
        resp = client.post(url, json=data, timeout=10)
    return resp.json()


def _send_message(chat_id: int, text: str, reply_to: int = None):
    """Send a text message back to the user."""
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_to:
        data["reply_to_message_id"] = reply_to
    return _send_telegram("sendMessage", data)


@router.post("/webhook/{token}")
async def webhook(request: Request, token: str):
    """
    Main Telegram webhook endpoint.
    Validates token in path, then routes to onboarding or agent.
    """
    # Validate token
    expected = _get_token()
    if not expected or token != expected:
        raise HTTPException(status_code=403, detail="Forbidden")

    # IP check disabled — Telegram webhooks come from their servers, not our VPS
    # TODO: re-enable for extra security once webhook is verified
    # _check_ip(request)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False}, status_code=400)

    # Handle edited messages
    edited_message = body.get("edited_message", {})
    if edited_message:
        return JSONResponse({"ok": True})

    message = body.get("message", {})
    if not message:
        return JSONResponse({"ok": True})

    chat_id = str(message.get("chat", {}).get("id", ""))
    message_id = message.get("message_id")

    if not chat_id:
        return JSONResponse({"ok": True})

    # Handle document uploads
    document = message.get("document")
    if document:
        await _handle_document(chat_id, document, message_id)
        return JSONResponse({"ok": True})

    text = message.get("text", "").strip()
    if not text:
        return JSONResponse({"ok": True})

    # Route to command or message handler
    try:
        if text.startswith("/"):
            await _handle_command(chat_id, text, message_id)
        else:
            await _handle_message(chat_id, text, message_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        _send_message(int(chat_id), f"⚠️ Error: {type(e).__name__}: {e}", message_id)

    return JSONResponse({"ok": True})


async def _handle_command(chat_id: str, text: str, message_id: int):
    """Handle /commands."""
    cmd = text.split()[0].lower()

    if cmd == "/start":
        _get_onboarding().start(chat_id, message_id, _send_message)
    elif cmd == "/help":
        _send_message(int(chat_id),
            "📊 <b>AnalystBot Commands</b>\n\n"
            "/start — Start or restart setup\n"
            "/help — Show this message\n"
            "/summary — Generate a sales report\n"
            "/myuploads — List your uploaded files\n"
            "/usage — Check your usage\n"
            "/reset — Reset conversation history",
            message_id)
    elif cmd == "/summary":
        result = _get_agent_loop().process(chat_id,
            "Generate a full sales summary and recommendations for my data.")
        _send_message(int(chat_id), result, message_id)
    elif cmd == "/myuploads":
        from tools.excel import list_files
        result = list_files(chat_id)
        _send_message(int(chat_id), result, message_id)
    elif cmd == "/usage":
        usage = _get_registry().ctx.get_usage(chat_id)
        used = usage.get("prompts_used", 0)
        limit = usage.get("limit", 500)
        remaining = max(0, limit - used)
        _send_message(int(chat_id),
            f"📊 <b>Usage</b>\n\nUsed: {used} / {limit}\nRemaining: {remaining}",
            message_id)
    elif cmd == "/reset":
        _get_registry().ctx.save_history(chat_id, [])
        _send_message(int(chat_id), "🔄 Conversation history cleared.", message_id)
    else:
        _send_message(int(chat_id),
            f"Unknown command: {cmd}. Type /help for available commands.",
            message_id)


async def _handle_message(chat_id: str, text: str, message_id: int):
    """Handle regular text messages."""
    config = _get_registry().ctx.get_config(chat_id)

    if not config.get("data_sources"):
        _get_onboarding().continue_flow(chat_id, text, message_id, _send_message)
        return

    result = _get_agent_loop().process(chat_id, text)
    _send_message(int(chat_id), result, message_id)


async def _handle_document(chat_id: str, document: dict, message_id: int):
    """Handle a file upload via Telegram document."""
    file_id = document.get("file_id")
    filename = document.get("file_name", "uploaded_file")
    mime_type = document.get("mime_type", "")

    allowed_mimes = {
        "text/csv": ".csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.ms-excel": ".xls",
    }
    ext = allowed_mimes.get(mime_type)
    if not ext:
        _send_message(int(chat_id),
            "❌ Unsupported file type. Please upload a CSV or Excel (.xlsx/.xls) file.",
            message_id)
        return

    if not filename.endswith(ext):
        filename += ext

    try:
        file_content = await _download_telegram_file(file_id)
    except Exception as e:
        _send_message(int(chat_id), f"❌ Failed to download file: {e}", message_id)
        return

    try:
        path = _get_registry().ctx.upload_file(chat_id, filename, file_content)
        config = _get_registry().ctx.get_config(chat_id)
        sources = config.get("data_sources", [])
        sources.append({"type": "file", "filename": filename, "label": filename})
        config["data_sources"] = sources
        _get_registry().ctx.save_config(chat_id, config)

        _send_message(int(chat_id),
            f"✅ File '{filename}' saved! I'll analyse it now.",
            message_id)

        # Auto-analyse
        from tools.excel import read_csv, read_excel
        data = read_csv(chat_id, filename) if filename.endswith(".csv") else read_excel(chat_id, filename)
        result = _get_agent_loop().process(chat_id,
            f"Analyse this data and give me a sales summary:\n\n{data[:3000]}")
        _send_message(int(chat_id), result)
    except Exception as e:
        _send_message(int(chat_id), f"❌ Error saving file: {e}", message_id)


async def _download_telegram_file(file_id: str) -> bytes:
    """Download a file from Telegram using the bot token (async)."""
    token = _get_token()
    get_url = f"{TELEGRAM_API}/bot{token}/getFile?file_id={file_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(get_url, timeout=10)
    result = resp.json()
    if not result.get("ok"):
        raise Exception(f"Telegram API error: {result}")

    file_path = result["result"]["file_path"]
    download_url = f"{TELEGRAM_API}/file/bot{token}/{file_path}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(download_url, timeout=30)
    return resp.content
