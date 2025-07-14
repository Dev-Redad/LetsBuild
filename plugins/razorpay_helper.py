import requests
import time

RAZORPAY_KEY_ID = "rzp_live_Kfvz8iobE8iUZc"
RAZORPAY_KEY_SECRET = "bcPhJQ2pHTaaF94FhWCEl6eD"

def create_payment_link(amount=2, user_name="Telegram User", user_email="user@example.com", purpose="File Access"):
    url = "https://api.razorpay.com/v1/payment_links"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "amount": amount * 100,
        "currency": "INR",
        "accept_partial": False,
        "description": purpose,
        "customer": {
            "name": user_name,
            "email": user_email,
            "contact": "9999999999"
        },
        "notify": {
            "sms": False,
            "email": False
        },
        "reminder_enable": True,
        "callback_url": "https://example.com/callback",
        "callback_method": "get"
    }
    response = requests.post(url, json=payload, auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    return response.json()

def poll_payment_status(payment_link_id, max_attempts=10, delay=5):
    url = f"https://api.razorpay.com/v1/payment_links/{payment_link_id}"
    for attempt in range(max_attempts):
        response = requests.get(url, auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        data = response.json()
        if data.get("status") == "paid":
            return True
        time.sleep(delay)
    return False
