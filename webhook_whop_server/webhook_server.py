# webhook_server.py
from fastapi import FastAPI, Request
import uvicorn
import json
import os
import requests

app = FastAPI()

# Get the URL from Render's Environment Variables (we set this later)
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def send_discord_alert(data):
    if not DISCORD_WEBHOOK_URL:
        print("Error: No Discord URL found in environment variables.")
        return

    payload_data = data.get('data', {})
    product_info = payload_data.get('product') or {}
    product_title = product_info.get('title', 'Unknown Product')
    
    user_info = payload_data.get('user') or {}
    email = user_info.get('email') or payload_data.get('email', 'N/A')
    
    amount = payload_data.get('total') or payload_data.get('final_amount', 'N/A')
    currency = payload_data.get('currency', 'USD').upper()
    status = payload_data.get('status', 'failed')
    
    message = {
        "content": "🚨 **Payment Failed Alert** 🚨",
        "embeds": [
            {
                "title": f"Failed: {product_title}",
                "color": 16711680,
                "fields": [
                    {"name": "Product", "value": str(product_title), "inline": False},
                    {"name": "Email", "value": str(email), "inline": True},
                    {"name": "Amount", "value": f"{amount} {currency}", "inline": True},
                    {"name": "Status", "value": str(status), "inline": False},
                    {"name": "Event ID", "value": data.get('id', 'N/A'), "inline": False}
                ],
                "footer": {"text": "Whop Webhook System"}
            }
        ]
    }
    
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=message)
        print("-> Discord alert sent!")
    except Exception as e:
        print(f"Failed to send Discord alert: {e}")

@app.post("/webhook")
async def receive_webhook(request: Request):
    data = await request.json()
    event_type = data.get('type')
    
    # Note: On Render Free Tier, saving to a file (whop_data.json) 
    # is temporary. It gets wiped when the server restarts. 
    # We will focus on the Discord Alert for now.
    
    if event_type in ['payment.failed', 'payment_failed']:
        send_discord_alert(data)
        
    return {"status": "ok"}

# This block is for local testing only. 
# Render runs the app using the command we give it in the dashboard.
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)