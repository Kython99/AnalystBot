"""
Vercel Python serverless entry point for AnalystBot.
Wrapped with Mangum for Vercel's Python runtime.
"""
import os

# Set data dir for ephemeral /tmp storage on Vercel serverless
os.environ.setdefault("ANALYSTBOT_DATA_DIR", "/tmp/analystbot-data")

from mangum import Mangum
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

DATA_DIR = "/tmp/analystbot-data"
os.makedirs(DATA_DIR, exist_ok=True)

app = FastAPI(title="AnalystBot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.vercel.app", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routes
from gateway.telegram import router as telegram_router
from payments.stripe_webhook import router as stripe_router

app.include_router(telegram_router)
app.include_router(stripe_router)


@app.get("/healthz")
async def health():
    return {"status": "ok", "service": "AnalystBot"}


@app.get("/readyz")
async def ready():
    return {"status": "ready"}


@app.get("/")
async def landing():
    return HTMLResponse(content=LANDING_HTML)


@app.get("/pricing")
async def pricing():
    return HTMLResponse(content=PRICING_HTML)


@app.get("/success")
async def success():
    return HTMLResponse(content=SUCCESS_HTML)


LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AnalystBot — AI Sales Intelligence</title>
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    :root{--bg:#0a0a0f;--surface:#13131a;--border:#1e1e2e;--accent:#6366f1;--accent-light:#818cf8;--text:#f1f5f9;--text-muted:#94a3b8;--green:#22c55e}
    body{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
    .container{max-width:900px;margin:0 auto;padding:0 24px}
    nav{padding:20px 0;border-bottom:1px solid var(--border)}
    nav .container{display:flex;justify-content:space-between;align-items:center}
    .logo{font-size:1.25rem;font-weight:700}
    .logo span{color:var(--accent)}
    nav a{color:var(--text-muted);text-decoration:none;font-size:0.9rem;margin-left:24px;transition:color 0.2s}
    nav a:hover{color:var(--text)}
    .hero{padding:100px 0 80px;text-align:center}
    .hero h1{font-size:3.5rem;font-weight:800;line-height:1.1;margin-bottom:24px;letter-spacing:-0.03em}
    .hero h1 span{color:var(--accent)}
    .hero p{font-size:1.25rem;color:var(--text-muted);max-width:600px;margin:0 auto 40px}
    .cta-btn{display:inline-block;background:var(--accent);color:white;padding:14px 32px;border-radius:8px;font-weight:600;text-decoration:none;font-size:1rem;transition:background 0.2s,transform 0.2s}
    .cta-btn:hover{background:var(--accent-light);transform:translateY(-1px)}
    .how{padding:80px 0}
    .section-label{font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--accent);font-weight:600;margin-bottom:12px}
    .section-title{font-size:2rem;font-weight:700;margin-bottom:48px}
    .steps{display:grid;grid-template-columns:repeat(3,1fr);gap:32px}
    .step{padding:24px;background:var(--surface);border:1px solid var(--border);border-radius:12px}
    .step-num{font-size:2rem;font-weight:800;color:var(--accent);margin-bottom:12px}
    .step h3{font-size:1.1rem;margin-bottom:8px}
    .step p{font-size:0.9rem;color:var(--text-muted)}
    .features{padding:80px 0}
    .features-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:20px}
    .feature{padding:28px;background:var(--surface);border:1px solid var(--border);border-radius:12px}
    .feature h3{font-size:1.1rem;margin-bottom:8px}
    .feature p{font-size:0.9rem;color:var(--text-muted)}
    .feature-icon{font-size:1.5rem;margin-bottom:12px}
    .pricing-cta{padding:80px 0;text-align:center;background:var(--surface);border-top:1px solid var(--border);border-bottom:1px solid var(--border)}
    .pricing-cta p{color:var(--text-muted);margin:20px 0}
    footer{padding:40px 0;text-align:center;color:var(--text-muted);font-size:0.85rem}
    @media(max-width:700px){.steps,.features-grid{grid-template-columns:1fr}.hero h1{font-size:2.5rem}}
  </style>
</head>
<body>
<nav><div class="container"><div class="logo">Analyst<span>Bot</span></div><div><a href="/">Home</a><a href="/pricing">Pricing</a></div></div></nav>
<section class="hero"><div class="container"><h1>Your sales data,<br><span>analysed instantly.</span></h1><p>Connect your spreadsheets and get AI-powered sales summaries, trend analysis, and actionable recommendations — right from Telegram.</p><a href="/pricing" class="cta-btn">Get Started — $10/month</a></div></section>
<section class="how"><div class="container"><p class="section-label">How it works</p><h2 class="section-title">From raw data to clear insights<br>in three steps.</h2><div class="steps"><div class="step"><div class="step-num">1</div><h3>Connect your data</h3><p>Upload a CSV, paste a Google Sheets link, or connect your database. Takes under a minute.</p></div><div class="step"><div class="step-num">2</div><h3>AI analyses your sales</h3><p>AnalystBot reads your data, calculates key metrics, and spots trends you'd otherwise miss.</p></div><div class="step"><div class="step-num">3</div><h3>Ask anything</h3><p>Follow-up questions in plain English. "What dropped last quarter?" "Show me top 5 products."</p></div></div></div></section>
<section class="features"><div class="container"><p class="section-label">Features</p><h2 class="section-title">Everything you need to<br>understand your sales.</h2><div class="features-grid"><div class="feature"><div class="feature-icon">📊</div><h3>Automatic Summaries</h3><p>Get a full sales breakdown — totals, averages, trends, top products — without lifting a finger.</p></div><div class="feature"><div class="feature-icon">💬</div><h3>Conversational Q&A</h3><p>Ask follow-up questions in plain English. No pivot tables, no Excel tricks needed.</p></div><div class="feature"><div class="feature-icon">🔗</div><h3>Google Sheets + CSV + Excel</h3><p>Works with whatever format your sales data is already in. No migration needed.</p></div><div class="feature"><div class="feature-icon">⚡</div><h3>Instant Setup</h3><p>Connect in under a minute via Telegram. No dashboards to configure, no training required.</p></div><div class="feature"><div class="feature-icon">🔒</div><h3>Your Data Stays Private</h3><p>Data is processed and stored only for your account. Isolated per customer, always.</p></div><div class="feature"><div class="feature-icon">📈</div><h3>Actionable Recommendations</h3><p>Not just numbers — AnalystBot tells you what's dropping, what's growing, and what to do next.</p></div></div></div></section>
<section class="pricing-cta"><div class="container"><h2>Ready to understand your sales?</h2><p>Plans from $10/month. Cancel anytime.</p><a href="/pricing" class="cta-btn">View Pricing</a></div></section>
<footer><div class="container"><p>© 2026 AnalystBot</p></div></footer>
</body>
</html>"""

PRICING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Pricing — AnalystBot</title>
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    :root{--bg:#0a0a0f;--surface:#13131a;--border:#1e1e2e;--accent:#6366f1;--accent-light:#818cf8;--text:#f1f5f9;--text-muted:#94a3b8;--green:#22c55e}
    body{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
    .container{max-width:900px;margin:0 auto;padding:0 24px}
    nav{padding:20px 0;border-bottom:1px solid var(--border)}
    nav .container{display:flex;justify-content:space-between;align-items:center}
    .logo{font-size:1.25rem;font-weight:700}
    .logo span{color:var(--accent)}
    nav a{color:var(--text-muted);text-decoration:none;font-size:0.9rem;margin-left:24px}
    .pricing-hero{padding:80px 0 60px;text-align:center}
    .pricing-hero h1{font-size:2.5rem;font-weight:800;margin-bottom:16px}
    .pricing-hero p{color:var(--text-muted);font-size:1.1rem}
    .plans{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;padding:20px 0 80px}
    .plan{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:32px;display:flex;flex-direction:column}
    .plan.featured{border-color:var(--accent);position:relative}
    .plan-badge{position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:var(--accent);color:white;font-size:0.75rem;font-weight:600;padding:4px 12px;border-radius:20px}
    .plan-name{font-size:1.1rem;font-weight:600;margin-bottom:8px}
    .plan-price{font-size:2.5rem;font-weight:800;margin-bottom:4px}
    .plan-price span{font-size:1rem;font-weight:400;color:var(--text-muted)}
    .plan-desc{font-size:0.85rem;color:var(--text-muted);margin-bottom:24px;min-height:40px}
    .plan-features{list-style:none;margin-bottom:32px;flex:1}
    .plan-features li{font-size:0.9rem;padding:6px 0;color:var(--text-muted)}
    .plan-features li::before{content:"✓ ";color:var(--green);margin-right:8px;font-weight:600}
    .plan-btn{display:block;text-align:center;padding:12px;border-radius:8px;font-weight:600;text-decoration:none;font-size:0.95rem;transition:all 0.2s;cursor:pointer;border:none}
    .plan-btn.primary{background:var(--accent);color:white}
    .plan-btn.primary:hover{background:var(--accent-light)}
    .plan-btn.secondary{background:var(--border);color:var(--text)}
    footer{padding:40px 0;text-align:center;color:var(--text-muted);font-size:0.85rem;border-top:1px solid var(--border)}
    @media(max-width:700px){.plans{grid-template-columns:1fr}}
  </style>
</head>
<body>
<nav><div class="container"><div class="logo">Analyst<span>Bot</span></div><div><a href="/">Home</a><a href="/pricing">Pricing</a></div></div></nav>
<section class="pricing-hero"><div class="container"><h1>Simple, honest pricing.</h1><p>Start free. Pay $10/month when you're ready.</p></div></section>
<section class="container">
  <div class="plans">
    <div class="plan">
      <div class="plan-name">Starter</div>
      <div class="plan-price">$10<span>/mo</span></div>
      <div class="plan-desc">For small teams getting started with sales data.</div>
      <ul class="plan-features"><li>500 prompts/month</li><li>1 data source</li><li>CSV + Excel uploads</li><li>Google Sheets</li><li>Basic summaries</li><li>Telegram access</li></ul>
      <button class="plan-btn primary" onclick="subscribe('starter')">Subscribe — Starter</button>
    </div>
    <div class="plan featured">
      <div class="plan-badge">Most Popular</div>
      <div class="plan-name">Growth</div>
      <div class="plan-price">$25<span>/mo</span></div>
      <div class="plan-desc">For growing businesses with more data needs.</div>
      <ul class="plan-features"><li>2,000 prompts/month</li><li>3 data sources</li><li>CSV + Excel uploads</li><li>Google Sheets</li><li>Trend analysis</li><li>Telegram access</li></ul>
      <button class="plan-btn primary" onclick="subscribe('growth')">Subscribe — Growth</button>
    </div>
    <div class="plan">
      <div class="plan-name">Pro</div>
      <div class="plan-price">$50<span>/mo</span></div>
      <div class="plan-desc">For power users who need the full picture.</div>
      <ul class="plan-features"><li>Unlimited prompts</li><li>All data sources</li><li>Dashboard access</li><li>Priority support</li><li>Custom integrations</li><li>API access (future)</li></ul>
      <button class="plan-btn secondary" onclick="subscribe('pro')">Subscribe — Pro</button>
    </div>
  </div>
</section>
<script>
async function subscribe(plan) {
  alert('Checkout coming soon! For now, message the Telegram bot to get started.');
}
</script>
<footer><div class="container"><p>© 2026 AnalystBot · Secure payments via Stripe</p></div></footer>
</body>
</html>"""

SUCCESS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Payment Successful — AnalystBot</title>
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    :root{--bg:#0a0a0f;--surface:#13131a;--border:#1e1e2e;--accent:#6366f1;--text:#f1f5f9;--text-muted:#94a3b8;--green:#22c55e}
    body{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;align-items:center;justify-content:center}
    .card{background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:60px 48px;text-align:center;max-width:480px;width:90%}
    .icon{font-size:4rem;margin-bottom:24px}
    h1{font-size:1.75rem;font-weight:700;margin-bottom:12px}
    p{color:var(--text-muted);margin-bottom:32px;line-height:1.6}
    .plan-tag{display:inline-block;background:var(--accent);color:white;padding:4px 12px;border-radius:20px;font-size:0.85rem;font-weight:600;margin-bottom:24px}
    .next-steps{background:var(--bg);border-radius:12px;padding:20px;text-align:left;margin-bottom:28px}
    .next-steps h3{font-size:0.9rem;text-transform:uppercase;letter-spacing:0.08em;color:var(--text-muted);margin-bottom:12px}
    .next-steps ol{padding-left:20px}
    .next-steps li{font-size:0.9rem;color:var(--text-muted);padding:4px 0}
    .telegram-btn{display:inline-block;background:#26A5E4;color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:1rem}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">✅</div>
    <div class="plan-tag" id="plan-tag">Starter Plan</div>
    <h1>Payment Successful!</h1>
    <p>Your subscription is active. Head to Telegram to start analysing your sales data.</p>
    <div class="next-steps">
      <h3>Next Steps</h3>
      <ol>
        <li>Open Telegram and search for your bot</li>
        <li>Send /start to activate your account</li>
        <li>Connect your sales data (Google Sheets or CSV)</li>
        <li>Ask your first question!</li>
      </ol>
    </div>
    <a href="https://t.me/SAnalystAgentBot" class="telegram-btn" target="_blank">Open Telegram Bot →</a>
  </div>
  <script>
    const params = new URLSearchParams(window.location.search);
    const plan = params.get('plan') || 'starter';
    const planNames = { starter: 'Starter', growth: 'Growth', pro: 'Pro' };
    document.getElementById('plan-tag').textContent = (planNames[plan] || 'Starter') + ' Plan';
  </script>
</body>
</html>"""

# Vercel serverless handler
handler = Mangum(app, lifespan="off")
