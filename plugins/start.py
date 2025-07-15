# (©)CodeXBotz
import asyncio
import base64
import logging
import os
import random
import re
import string
import time

import razorpay
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import Bot
from config import (
    ADMINS,
    FORCE_MSG,
    START_MSG,
    CUSTOM_CAPTION,
    DISABLE_CHANNEL_BUTTON,
    PROTECT_CONTENT,
)
from helper_func import (
    subscribed,
    encode,
    decode,
    get_messages,
)
from database.database import add_user, del_user, full_userbase, present_user

# Razorpay client setup
razorpay_client = razorpay.Client(auth=("rzp_live_Kfvz8iobE8iUZc", "bcPhJQ2pHTaaF94FhWCEl6eD"))

# Store user batch data in memory
Bot.batch_data = {}

@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    id = message.from_user.id
    owner_id = ADMINS

    if id == owner_id:
        return await message.reply("You are the owner! Additional actions can be added here.")

    if not await present_user(id):
        try:
            await add_user(id)
        except:
            pass

    if len(message.text) > 7:
        try:
            base64_string = message.text.split(" ", 1)[1]
        except:
            return

        _string = await decode(base64_string)
        argument = _string.split("-")

        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end = int(int(argument[2]) / abs(client.db_channel.id))
            except:
                return
            ids = list(range(start, end + 1)) if start <= end else list(range(start, end - 1, -1))
        elif len(argument) == 2:
            try:
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]
            except:
                return
        else:
            return

        # Store batch for the user before generating payment
        client.batch_data[id] = ids

        # Create Razorpay payment
        order = razorpay_client.order.create({
            "amount": 200,  # ₹2 in paise
            "currency": "INR",
            "payment_capture": 1
        })

        order_id = order['id']
        client.batch_data[id] = {
            "ids": ids,
            "order_id": order_id
        }

        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=https://rzp.io/i/{order['id']}"
        pay_url = f"https://rzp.io/i/{order['id']}"

        buttons = [
            [InlineKeyboardButton("I've Paid ✅", callback_data=f"checkpayment_{order_id}")]
        ]

        await message.reply_photo(
            photo=qr_url,
            caption=f"Pay ₹2 to access your files.\n\n[Pay Now]({pay_url})",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    else:
        reply_markup = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("About Me", callback_data="about"),
                InlineKeyboardButton("Close", callback_data="close")
            ]]
        )
        await message.reply_text(
            text=START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            quote=True
        )

@Bot.on_callback_query(filters.regex("^checkpayment_"))
async def check_payment(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    order_id = callback_query.data.split("_", 1)[1]

    try:
        payments = razorpay_client.order.payments(order_id)
        success = any(p.get("status") == "captured" for p in payments.get("items", []))
    except Exception as e:
        return await callback_query.message.edit_text("Failed to check payment status. Please try again later.")

    if success:
        data = client.batch_data.get(user_id)
        if not data:
            return await callback_query.message.edit_text("Batch expired or not found.")

        ids = data['ids']
        try:
            messages = await get_messages(client, ids)
        except:
            return await callback_query.message.edit_text("Failed to fetch messages. Please try again.")

        await callback_query.message.delete()

        for msg in messages:
            caption = (
                CUSTOM_CAPTION.format(
                    previouscaption="" if not msg.caption else msg.caption.html,
                    filename=msg.document.file_name
                ) if bool(CUSTOM_CAPTION) and bool(msg.document) else
                "" if not msg.caption else msg.caption.html
            )
            try:
                await msg.copy(
                    chat_id=user_id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=msg.reply_markup if not DISABLE_CHANNEL_BUTTON else None,
                    protect_content=PROTECT_CONTENT
                )
                await asyncio.sleep(0.5)
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await msg.copy(chat_id=user_id)
            except:
                pass

        del client.batch_data[user_id]
    else:
        await callback_query.answer("Payment not received yet. Try again after a few seconds.", show_alert=True)


@Bot.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text="<b>Processing ...</b>")
    users = await full_userbase()
    await msg.edit(f"{len(users)} users are using this bot")


@Bot.on_message(filters.private & filters.command('broadcast') & filters.user(ADMINS))
async def send_text(client: Bot, message: Message):
    if message.reply_to_message:
        query = await full_userbase()
        broadcast_msg = message.reply_to_message
        total = successful = blocked = deleted = unsuccessful = 0

        pls_wait = await message.reply("<i>Broadcasting Message.. This will take some time</i>")
        for chat_id in query:
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await broadcast_msg.copy(chat_id)
                successful += 1
            except UserIsBlocked:
                await del_user(chat_id)
                blocked += 1
            except InputUserDeactivated:
                await del_user(chat_id)
                deleted += 1
            except:
                unsuccessful += 1
            total += 1

        status = (
            f"<b><u>Broadcast Completed</u>\n\n"
            f"Total Users: <code>{total}</code>\n"
            f"Successful: <code>{successful}</code>\n"
            f"Blocked Users: <code>{blocked}</code>\n"
            f"Deleted Accounts: <code>{deleted}</code>\n"
            f"Unsuccessful: <code>{unsuccessful}</code></b>"
        )

        return await pls_wait.edit(status)
    else:
        msg = await message.reply(
            "<code>Use this command as a reply to any Telegram message without any spaces.</code>"
        )
        await asyncio.sleep(8)
        await msg.delete()
