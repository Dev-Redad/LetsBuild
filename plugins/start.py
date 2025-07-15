import os
import time
import logging
import asyncio
import razorpay
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from plugins.database.files import add_user, get_file_details
from datetime import datetime
from PIL import Image
import qrcode
from io import BytesIO

# Hardcoded Razorpay credentials
RAZORPAY_KEY_ID = "rzp_live_Kfvz8iobE8iUZc"
RAZORPAY_KEY_SECRET = "bcPhJQ2pHTaaF94FhWCEl6eD"

# Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Dictionary to track paid users
paid_users = {}

app = Client(
    "bot",
    api_id=25533814,
    api_hash="1df47b6c8c43b3c62533eed9abaf8ef9",
    bot_token="7309627863:AAGBUCS7TIwCyuQirneqpXDxdYaSmNKQGDE"
)

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    user = message.from_user
    await add_user(user.id)

    if len(message.command) > 1:
        file_id = message.command[1]
        if user.id in paid_users and paid_users[user.id] == file_id:
            file_details = await get_file_details(file_id)
            if file_details:
                await message.reply_cached_media(file_id, caption=file_details.get("caption"))
                return
            else:
                await message.reply("❌ File not found.")
                return

        # User has not paid yet → send Razorpay Payment Link
        try:
            payment = razorpay_client.payment_link.create({
                "amount": 200,  # ₹2 in paise
                "currency": "INR",
                "description": f"File Access Fee for File ID {file_id}",
                "customer": {
                    "name": user.first_name,
                    "email": f"{user.id}@example.com",
                    "contact": "9123456789"
                },
                "notify": {"sms": False, "email": False},
                "callback_url": "https://t.me/{client.me.username}?start={file_id}",
                "callback_method": "get"
            })

            link = payment['short_url']

            # Generate QR code
            qr = qrcode.make(link)
            bio = BytesIO()
            bio.name = 'qr.png'
            qr.save(bio, 'PNG')
            bio.seek(0)

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Pay ₹2 to Unlock", url=link)],
                [InlineKeyboardButton("I've Paid", callback_data=f"verify_{file_id}")]
            ])

            await client.send_photo(
                chat_id=message.chat.id,
                photo=bio,
                caption="<b>Pay ₹2 via Razorpay to access the file.</b>",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            await message.reply(f"❌ Failed to create payment link.\nError: {e}")
    else:
        await message.reply("Hello! Send me a file link to begin.")

@app.on_callback_query(filters.regex("^verify_"))
async def verify_payment(client, callback_query):
    user_id = callback_query.from_user.id
    file_id = callback_query.data.split("_", 1)[1]

    try:
        # Check if payment link was paid manually
        links = razorpay_client.payment_link.all()
        for link in links['items']:
            if link['description'].endswith(file_id) and link['status'] == 'paid' and f"{user_id}@example.com" in link['customer']['email']:
                paid_users[user_id] = file_id
                await callback_query.message.edit_text("✅ Payment verified! Please tap the file link again to access your file.")
                return
        await callback_query.message.edit_text("❌ Payment not found yet. Please complete it and try again in a moment.")
    except Exception as e:
        await callback_query.message.edit_text(f"❌ Error verifying payment: {e}")


if __name__ == '__main__':
    import asyncio
    if not app.is_running:
        app.run()
    else:
        asyncio.get_event_loop().run_until_complete(app.start())
