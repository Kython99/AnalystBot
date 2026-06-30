"""
Onboarding flow — walks new customers through setup via Telegram chat.
State machine: new → source_type → await_url → await_file → complete
"""
import re

from tenants.registry import TenantRegistry


class OnboardingFlow:
    """
    Multi-step onboarding state machine per tenant.

    State transitions:
      new → source_type (ask what data source)
      source_type → await_url (if Google Sheets)
      source_type → await_file (if CSV upload)
      await_url → complete (store URL)
      await_file → complete (store file)
    """

    # States
    STATE_NEW = "new"
    STATE_SOURCE_TYPE = "source_type"
    STATE_AWAIT_URL = "await_url"
    STATE_AWAIT_FILE = "await_file"
    STATE_COMPLETE = "complete"

    def __init__(self, data_dir: str = "/tmp/analystbot-data"):
        self.registry = TenantRegistry(data_dir)
        self._states: dict[str, str] = {}
        self._partial: dict[str, dict] = {}

    def _get_state(self, tenant_id: str) -> str:
        return self._states.get(tenant_id, self.STATE_NEW)

    def _set_state(self, tenant_id: str, state: str):
        self._states[tenant_id] = state

    def start(self, chat_id: str, message_id: int, send_fn):
        """Send the welcome message and ask for data source type."""
        self._set_state(chat_id, self.STATE_SOURCE_TYPE)
        send_fn(
            int(chat_id),
            (
                "👋 Welcome to <b>AnalystBot</b>!\n\n"
                "I analyse your sales data and give you instant insights.\n\n"
                "📂 <b>What data source do you want to connect?</b>\n\n"
                "1️⃣ <b>Google Sheets</b> — paste a shareable link (fastest)\n"
                "2️⃣ <b>CSV file</b> — upload your sales export\n"
                "3️⃣ <b>Excel file</b> — upload .xlsx\n\n"
                "Reply with the number (1, 2, or 3)"
            ),
            message_id,
        )

    def continue_flow(self, chat_id: str, text: str, message_id: int, send_fn):
        """Continue the onboarding flow based on current state."""
        state = self._get_state(chat_id)
        text = text.strip()

        if state == self.STATE_NEW:
            self.start(chat_id, message_id, send_fn)
            return

        if state == self.STATE_SOURCE_TYPE:
            self._handle_source_type(chat_id, text, message_id, send_fn)
            return

        if state == self.STATE_AWAIT_URL:
            self._handle_url(chat_id, text, message_id, send_fn)
            return

        if state == self.STATE_AWAIT_FILE:
            self._handle_file(chat_id, text, message_id, send_fn)
            return

        if state == self.STATE_COMPLETE:
            send_fn(
                int(chat_id),
                "✅ You're already set up! Just send me a question about your sales data.",
                message_id,
            )

    def _handle_source_type(self, chat_id: str, text: str, message_id: int, send_fn):
        """Process the data source type selection."""
        if text == "1":
            self._set_state(chat_id, self.STATE_AWAIT_URL)
            send_fn(
                int(chat_id),
                (
                    "🔗 <b>Google Sheets</b>\n\n"
                    "1. Open your sheet in Google Sheets\n"
                    "2. Click <b>Share</b> → <b>Anyone with the link</b>\n"
                    "3. Copy the link and paste it here\n\n"
                    "Make sure the sheet is set to <b>'Anyone with the link can view'</b>"
                ),
                message_id,
            )
        elif text in ("2", "3"):
            self._set_state(chat_id, self.STATE_AWAIT_FILE)
            file_type = "CSV" if text == "2" else "Excel (.xlsx)"
            send_fn(
                int(chat_id),
                f"📁 <b>{file_type} upload</b>\n\nSend me your file directly in this chat.",
                message_id,
            )
        else:
            send_fn(
                int(chat_id),
                "Please reply with 1, 2, or 3 to choose your data source.",
                message_id,
            )

    def _handle_url(self, chat_id: str, text: str, message_id: int, send_fn):
        """Validate and store the Google Sheets URL."""
        if not re.search(r"docs\.google\.com/spreadsheets", text):
            send_fn(
                int(chat_id),
                "❌ That doesn't look like a Google Sheets link. Please paste a full URL like:\nhttps://docs.google.com/spreadsheets/d/.../edit",
                message_id,
            )
            return

        # Save the URL to config
        config = self.registry.ctx.get_config(chat_id)
        sources = config.get("data_sources", [])
        sources.append({"type": "google_sheets", "url": text, "label": "Google Sheets"})
        config["data_sources"] = sources
        self.registry.ctx.save_config(chat_id, config)

        self._set_state(chat_id, self.STATE_COMPLETE)
        send_fn(
            int(chat_id),
            (
                "✅ <b>Google Sheets connected!</b>\n\n"
                "I'll read your data and start analysing now.\n"
                "Try asking me something like:\n"
                "\"Summarise my sales\"\n"
                "\"What were my best products?\"\n"
                "\"Show me trends over time\""
            ),
            message_id,
        )

        # Trigger initial analysis
        from core.agent_loop import AgentLoop
        loop = AgentLoop()
        result = loop.process(
            chat_id,
            "Analyse my connected data source and give me a summary of my sales performance."
        )
        send_fn(int(chat_id), result)

    def _handle_file(self, chat_id: str, text: str, message_id: int, send_fn):
        """Handle file upload during onboarding."""
        send_fn(
            int(chat_id),
            "📎 File upload detected! Please send the file as a document attachment in Telegram (not as text).",
            message_id,
        )
