"""
Stripe utilities — create Checkout sessions and manage subscriptions.
"""
import os
import stripe
from typing import Optional

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

PLANS = {
    "starter": {
        "name": "Starter",
        "price": 1000,  # $10.00 in cents
        "price_id": os.getenv("STRIPE_PRICE_STARTER", ""),  # Set in Stripe dashboard
        "description": "500 prompts/month · 1 data source",
    },
    "growth": {
        "name": "Growth",
        "price": 2500,  # $25.00
        "price_id": os.getenv("STRIPE_PRICE_GROWTH", ""),
        "description": "2,000 prompts/month · 3 data sources",
    },
    "pro": {
        "name": "Pro",
        "price": 5000,  # $50.00
        "price_id": os.getenv("STRIPE_PRICE_PRO", ""),
        "description": "Unlimited prompts · All data sources · Dashboard",
    },
}

APP_URL = os.getenv("APP_URL", "https://analystbot.vercel.app")


def create_checkout_session(
    plan: str,
    chat_id: str,
    success_url: str = None,
    cancel_url: str = None,
) -> str:
    """
    Create a Stripe Checkout session for a plan upgrade.

    Args:
        plan: Plan key (starter, growth, pro)
        chat_id: Telegram chat_id — stored in metadata for webhook lookup
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect if payment is cancelled

    Returns:
        The Stripe Checkout URL to redirect the user to
    """
    if plan not in PLANS:
        raise ValueError(f"Unknown plan: {plan}")

    plan_info = PLANS[plan]

    success_url = success_url or f"{APP_URL}/success?plan={plan}&chat_id={chat_id}"
    cancel_url = cancel_url or f"{APP_URL}/pricing"

    if plan_info["price_id"]:
        # Use Price ID (recommended for subscriptions)
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": plan_info["price_id"], "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"chat_id": chat_id, "plan": plan},
        )
    else:
        # Fallback: one-time payment (if no Stripe products set up yet)
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"AnalystBot {plan_info['name']}",
                            "description": plan_info["description"],
                        },
                        "unit_amount": plan_info["price"],
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"chat_id": chat_id, "plan": plan},
        )

    return session.url


def create_portal_session(chat_id: str, return_url: str = None) -> str:
    """
    Create a Stripe Customer Portal session for managing subscriptions.
    """
    return_url = return_url or f"{APP_URL}/pricing"
    # In production, look up the Stripe customer_id for this chat_id
    # For now, return the portal URL
    portal_url = f"https://billing.stripe.com/p/login/{return_url}"
    return portal_url
