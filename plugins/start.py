import os
import razorpay
import uuid
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# Razorpay API Keys
razorpay_client = razorpay.Client(auth=("rzp_live_Kfvz8iobE8iUZc", "bcPhJQ2pHTaaF94FhWCEl6eD"))

# In-memory user data
user_payments = {}

# Create Pyrogram client
app = Client(
    "payment_bot",
    api_id=int(os.environ.get("API_ID")),
    api_hash=os.environ.get("API_HASH"),
    bot_token=os.environ.get("BOT_TOKEN")
)

@app.on_message(filters.private & filters.media)
async def handle_file(client, message: Message):
    user_id = message.from_user.id
    file_id = message.document.file_id if message.document else message.video.file_id if message.video else message.photo.file_id

    payment_id = str(uuid.uuid4())
    user_payments[user_id] = {
        "file_id": file_id,
        "paid": False,
        "payment_id": payment_id
    }

    order = razorpay_client.order.create({
        "amount": 200,  # ₹2 in paise
        "currency": "INR",
        "receipt": payment_id,
        "payment_capture": 1
    })

    pay_url = f"https://rzp.io/l/{order['id']}"

    await message.reply_photo(
        photo="https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=" + pay_url,
        caption=f"**Amount**: ₹2\n**Order ID**: `{order['id']}`\n\nClick the button below after payment.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 I’ve Paid", callback_data=f"check_payment:{order['id']}")]
        ]),
        parse_mode=enums.ParseMode.MARKDOWN
    )

@app.on_callback_query(filters.regex("check_payment:(.*)"))
async def check_payment_callback(client, callback_query):
    order_id = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id

    try:
        payments = razorpay_client.order.payments(order_id)
        paid = any(p["status"] == "captured" for p in payments["items"])

        if paid:
            if user_id in user_payments and not user_payments[user_id]["paid"]:
                user_payments[user_id]["paid"] = True
                file_id = user_payments[user_id]["file_id"]

                await client.send_document(
                    chat_id=user_id,
                    document=file_id,
                    caption="✅ Payment received. Here is your file.",
                    parse_mode=enums.ParseMode.MARKDOWN
                )
                await callback_query.message.delete()
            else:
                await callback_query.answer("Payment already processed or file missing.", show_alert=True)
        else:
            await callback_query.answer("❌ Payment not found. Please complete payment first.", show_alert=True)
    except Exception as e:
        await callback_query.answer("Error checking payment. Try again later.", show_alert=True)
        print("Payment check error:", str(e))

if __name__ == "__main__":
    app.run()
