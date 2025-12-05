# test_failure.py
import requests

url = "http://localhost:8000/webhook"

# A structure that mimics the REAL Whop JSON you pasted
payload = {
    "type": "payment.failed", # Matches real Whop event name
    "id": "msg_TEST_12345",
    "data": {
        "id": "pay_fake_123",
        "status": "payment_failed",
        "total": "99.00",
        "currency": "usd",
        "failure_message": "Insufficient funds",
        
        # This is the nested object we just added support for!
        "product": {
            "id": "prod_123",
            "title": "VIP Trading Access (Monthly)", 
            "route": "vip-trading"
        },
        
        "user": {
            "email": "sad_customer@gmail.com",
            "username": "sad_customer"
        }
    }
}

try:
    response = requests.post(url, json=payload)
    print(f"Sent. Status Code: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")