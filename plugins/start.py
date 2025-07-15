import asyncio
import razorpay
import qrcode
import io
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

# Telegram Bot Config
API_ID = 25533814
API_HASH = "1df47b6c8c43b3c62533eed9abaf8ef9"
BOT_TOKEN = "7309627863:AAGBUCS7TIwCyuQirneqpXDxdYaSmNKQGDE"
CHANNEL_ID = -1002767674889

# Razorpay Keys (Embedded directly)
RAZORPAY_KEY_ID = "rzp_live_Kfvz8iobE8iUZc"
RAZORPAY_KEY_SECRET = "bcPhJQ2pHTaaF94FhWCEl6eD"

# Init Bot and Razorpay
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Price per batch
AMOUNT_IN_RUPEES = 2

@bot.on_message(filters.private & filters.command("start"))
async def start(client, message: Message):
    await message.reply_text(
        "👋 Welcome! Send me a file link or command to get started."
    )

@bot.on_message(filters.private & filters.regex(r"^https://t\.me/c/\d+/\d+$"))
async def handle_file_request(client, message: Message):
    user_id = message.from_user.id
    amount_paise = AMOUNT_IN_RUPEES * 100

    # Create Razorpay Payment Link
    payment = razorpay_client.payment_link.create({
        "amount": amount_paise,
        "currency": "INR",
        "accept_partial": False,
        "description": "Access batch",
        "customer": {
            "name": str(user_id),
            "contact": "9123456780",  # optional dummy
            "email": f"user{user_id}@example.com"
        },
        "notify": {"sms": False, "email": False},
        "reminder_enable": False,
        "callback_url": "https://google.com",  # placeholder
        "callback_method": "get"
    })

    pay_link = payment['short_url']

    # Generate QR
    qr_img = qrcode.make(pay_link)
    qr_io = io.BytesIO()
    qr_img.save(qr_io, format='PNG')
    qr_io.seek(0)

    # Send payment link and QR
    await message.reply_photo(
        photo=qr_io,
        caption=f"💳 Please pay ₹{AMOUNT_IN_RUPEES} to access the batch.\n\nAfter paying, click 'I've Paid' below.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Pay Now", url=pay_link)],
            [InlineKeyboardButton("✅ I've Paid", callback_data=f"verify|{payment['id']}|{message.text}")]
        ])
    )

@bot.on_callback_query(filters.regex(r"^verify\|"))
async def verify_payment(client, callback_query):
    data = callback_query.data.split("|")
    payment_id, file_link = data[1], data[2]

    try:
        payment = razorpay_client.payment_link.fetch(payment_id)
        if payment['status'] == 'paid':
            await callback_query.message.reply(f"✅ Payment received. Here's your file:", quote=True)
            await client.copy_message(
                chat_id=callback_query.from_user.id,
                from_chat_id=CHANNEL_ID,
                message_id=int(file_link.split("/")[-1])
            )
        else:
            await callback_query.answer("❌ Payment not yet completed.", show_alert=True)
    except Exception as e:
        await callback_query.answer("⚠️ Error verifying payment.", show_alert=True)

# Run the bot
if __name__ == '__main__':
    bot.run()
