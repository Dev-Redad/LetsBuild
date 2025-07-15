# plugins/start.py

import razorpay
import time
import asyncio
import qrcode
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from main import Bot

# Razorpay credentials
RAZORPAY_KEY_ID = "rzp_live_Kfvz8iobE8iUZc"
RAZORPAY_KEY_SECRET = "bcPhJQ2pHTaaF94FhWCEl6eD"
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

payment_links = {}

@Bot.on_message(filters.command("start"))
async def start_handler(_, message: Message):
    await message.reply_text(
        "Send me a batch file link to continue (I charge ₹2 per batch)."
    )

@Bot.on_message(filters.text & filters.private)
async def handle_batch(_, message: Message):
    user_id = message.from_user.id
    if "batch" in message.text:
        # create payment link
        response = client.payment_link.create({
            "amount": 200,
            "currency": "INR",
            "description": "Payment for batch access",
            "customer": {
                "name": str(user_id),
                "email": f"{user_id}@example.com"
            },
            "notify": {"sms": False, "email": False},
            "reminder_enable": False,
            "callback_url": "https://t.me/your_bot_username",  # optional
            "callback_method": "get"
        })

        payment_url = response['short_url']
        payment_id = response['id']
        payment_links[user_id] = payment_id

        # Generate QR code
        img = qrcode.make(payment_url)
        qr_path = f"{user_id}_qr.png"
        img.save(qr_path)

        await message.reply_photo(
            photo=qr_path,
            caption="Pay ₹2 to access this batch.\nClick 'I’ve Paid' after payment.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("I’ve Paid ✅", callback_data=f"verify_{user_id}")]
            ])
        )
    else:
        await message.reply_text("I’m just a file share bot. Please send a valid batch link.")

@Bot.on_callback_query(filters.regex(r"^verify_\d+$"))
async def verify_payment(_, query):
    user_id = int(query.data.split("_")[1])
    payment_id = payment_links.get(user_id)

    if not payment_id:
        await query.message.reply_text("No payment initiated.")
        return

    payment = client.payment_link.fetch(payment_id)
    if payment['status'] == 'paid':
        await query.message.reply_text("✅ Payment verified! Sending your batch...")
        # TODO: Add file sending logic here
    else:
        await query.message.reply_text("❌ Payment not completed yet.")
