"""
Stripe webhook handler — processes payment events.
"""
import os
import stripe
from fastapi import APIRouter, Request, Header, HTTPException
from typing import Optional

from tenants.registry import TenantRegistry

router = APIRouter()
registry = TenantRegistry()

# Load Stripe keys from env
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
ALLOWED_IPS = os.getenv("ALLOWED_IPS", "187.127.100.76").split(",")


def _check_ip(request: Request):
    client_ip = request.client.host if request.client else None
    if client_ip not in ALLOWED_IPS:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, stripe-signature: Optional[str] = Header(None)):
    """
    Receive and process Stripe webhook events.

    Required events:
    - checkout.session.completed → activate tenant access
    - customer.subscription.updated/deleted → update plan
    - invoice.payment_failed → notify tenant
    """
    _check_ip(request)

    body = await request.body()

    if not stripe-signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        event = stripe.Webhook.construct_event(body, stripe-signature, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    chat_id = data.get("metadata", {}).get("chat_id")
    if not chat_id:
        return {"ok": True, "message": "No chat_id in metadata, skipping"}

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(chat_id, data)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(chat_id, data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(chat_id, data)
    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(chat_id, data)
    else:
        print(f"Unhandled event type: {event_type}")

    return {"ok": True}


def _handle_checkout_completed(chat_id: str, data: dict):
    """Payment successful — activate the tenant's plan."""
    plan = data.get("metadata", {}).get("plan", "starter")
    plan_limits = {"starter": 500, "growth": 2000, "pro": 999999}

    # Ensure tenant exists
    registry.get_or_create(chat_id)

    # Update plan and limit
    config = registry.ctx.get_config(chat_id)
    config["plan"] = plan
    config["stripe_session_id"] = data.get("id")
    config["subscription_active"] = True
    registry.ctx.save_config(chat_id, config)

    # Update usage limit
    usage = registry.ctx.get_usage(chat_id)
    usage["limit"] = plan_limits.get(plan, 500)
    registry.ctx.save_config(chat_id, config)

    print(f"✅ Activated plan '{plan}' for tenant {chat_id}")


def _handle_subscription_updated(chat_id: str, data: dict):
    """Subscription updated (plan change, renewal, etc.)."""
    status = data.get("status")
    plan = data.get("metadata", {}).get("plan", "starter")

    if status == "active":
        config = registry.ctx.get_config(chat_id)
        config["subscription_active"] = True
        registry.ctx.save_config(chat_id, config)
        print(f"✅ Subscription active for {chat_id}")
    elif status in ("past_due", "canceled"):
        config = registry.ctx.get_config(chat_id)
        config["subscription_active"] = False
        registry.ctx.save_config(chat_id, config)
        print(f"⚠️ Subscription {status} for {chat_id}")


def _handle_subscription_deleted(chat_id: str, data: dict):
    """Subscription cancelled — downgrade to free."""
    config = registry.ctx.get_config(chat_id)
    config["plan"] = "starter"
    config["subscription_active"] = False
    registry.ctx.save_config(chat_id, config)
    usage = registry.ctx.get_usage(chat_id)
    usage["limit"] = 500
    print(f"❌ Subscription cancelled for {chat_id}")


def _handle_payment_failed(chat_id: str, data: dict):
    """Payment failed — notify the tenant via Telegram."""
    # Send a Telegram message to the user
    import httpx
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        httpx.post(url, json={
            "chat_id": chat_id,
            "text": "⚠️ Your payment failed. Please update your payment method to keep your AnalystBot subscription active.",
        }, timeout=10)
    except Exception as e:
        print(f"Failed to notify {chat_id} about payment failure: {e}")
