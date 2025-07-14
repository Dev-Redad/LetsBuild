from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from config import ADMINS
from helper_func import encode, get_message_id
from .razorpay_helper import create_payment_link, poll_payment_status

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('batch'))
async def batch(client: Client, message: Message):
    while True:
        try:
            first_message = await client.ask(
                text="Forward the First Message from DB Channel (with Quotes)..\n\nor Send the DB Channel Post Link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except:
            return

        f_msg_id = await get_message_id(client, first_message)
        if f_msg_id:
            break
        else:
            await first_message.reply(
                "❌ Error\n\nthis Forwarded Post is not from my DB Channel or this Link is taken from DB Channel",
                quote=True
            )
            continue

    encoded_id = encode(f_msg_id)
    user_name = message.from_user.first_name or "Telegram User"

    
    payment = create_payment_link(user_name=user_name, purpose="File access ₹2")
    payment_url = payment.get("short_url")
    payment_id = payment.get("id")

    if not payment_url:
        await message.reply("❌ Failed to create payment link. Try again later.")
        return

    
    await message.reply(
        "💳 To access this file, please pay ₹2 using the button below.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Pay ₹2", url=payment_url)]
        ])
    )

    
    await message.reply("⏳ Waiting for payment confirmation...")
    paid = poll_payment_status(payment_id)

    if paid:
        await message.reply("✅ Payment received! Sending your file...")
        await client.copy_message(
            chat_id=message.chat.id,
            from_chat_id=-100,  # ← Replace with your DB Channel ID
            message_id=f_msg_id
        )
    else:
        await message.reply("❌ Payment not completed in time. Please try again.")
