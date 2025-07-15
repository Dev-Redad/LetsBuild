import os
import razorpay
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import TG_BOT_TOKEN, APP_ID, API_HASH, OWNER_ID

api_key = "rzp_live_Kfvz8iobE8iUZc"
api_secret = "bcPhJQ2pHTaaF94FhWCEl6eD"

bot = Client("PaymentBot", bot_token=TG_BOT_TOKEN, api_id=APP_ID, api_hash=API_HASH)
razorpay_client = razorpay.Client(auth=(api_key, api_secret))

payment_links = {}  # user_id -> payment_link_id

@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(
        "👋 Hello! Send me a file link to continue. Each batch costs ₹2.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Buy Now (₹2)", callback_data="pay")]]
        )
    )

@bot.on_callback_query(filters.regex("^pay"))
async def pay_cb(client, callback_query):
    user_id = callback_query.from_user.id
    payment = razorpay_client.payment_link.create({
        "amount": 200,
        "currency": "INR",
        "description": "Payment for file batch",
        "customer": {
            "name": str(callback_query.from_user.first_name),
            "contact": "9999999999",
            "email": f"{user_id}@example.com"
        },
        "notify": {
            "sms": False,
            "email": False
        },
        "callback_url": "https://example.com/",
        "callback_method": "get"
    })

    payment_links[user_id] = payment['id']
    pay_url = payment['short_url']

    await callback_query.message.reply_text(
        f"🧾 Please pay ₹2 using the link below:\n\n<code>{pay_url}</code>",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Pay Now", url=pay_url)],
             [InlineKeyboardButton("I've Paid", callback_data="verify")]]
        ),
        parse_mode="HTML"
    )

@bot.on_callback_query(filters.regex("^verify"))
async def verify_payment(client, callback_query):
    user_id = callback_query.from_user.id
    link_id = payment_links.get(user_id)

    if not link_id:
        await callback_query.answer("No payment record found.", show_alert=True)
        return

    payment_info = razorpay_client.payment_link.fetch(link_id)
    status = payment_info['status']

    if status == "paid":
        await callback_query.message.reply_text("✅ Payment confirmed! Sending your files...")
        # Send files here
    else:
        await callback_query.message.reply_text("❌ Payment not found or incomplete.")

print("Bot running...")
bot.run()
