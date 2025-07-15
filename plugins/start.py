# Updated start.py with Razorpay payment integration and ad-token removed
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
    OWNER_ID,
)
from helper_func import (
    subscribed,
    encode,
    decode,
    get_messages,
)
from database.database import add_user, del_user, full_userbase, present_user

RAZORPAY_KEY_ID = "rzp_live_Kfvz8iobE8iUZc"
RAZORPAY_KEY_SECRET = "bcPhJQ2pHTaaF94FhWCEl6eD"
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

user_orders = {}

@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    id = message.from_user.id
    if not await present_user(id):
        try:
            await add_user(id)
        except:
            pass

    if "pay_" in message.text:
        _, order_id, encoded = message.text.split("_")
        payment = razorpay_client.order.fetch(order_id)
        if payment['status'] == 'paid':
            base64_string = encoded
            await send_files(client, message, base64_string)
        else:
            await message.reply("Payment not completed. Please pay and click 'I've Paid' again.")
        return

    elif len(message.text) > 7:
        try:
            base64_string = message.text.split(" ", 1)[1]
        except:
            return

        order = razorpay_client.order.create({
            "amount": 200,  # 2 INR in paise
            "currency": "INR",
            "payment_capture": 1
        })

        payment_url = f"https://rzp.io/l/{order['id']}"
        user_orders[id] = {"order_id": order['id'], "encoded": base64_string}

        await message.reply(
            f"To access this file, please pay ₹2.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Pay ₹2", url=payment_url)],
                [InlineKeyboardButton("I've Paid", callback_data=f"checkpay_{order['id']}")]
            ])
        )
    else:
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("About Me", callback_data="about"),
             InlineKeyboardButton("Close", callback_data="close")]
        ])
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

@Bot.on_callback_query(filters.regex("checkpay_"))
async def check_payment(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    order_id = query.data.split("checkpay_")[1]

    try:
        payment = razorpay_client.order.fetch(order_id)
        if payment['status'] == 'paid':
            encoded = user_orders[user_id]['encoded']
            await send_files(bot, query.message, encoded)
            await query.message.delete()
        else:
            await query.answer("Payment not completed yet.", show_alert=True)
    except Exception as e:
        logging.error(str(e))
        await query.answer("Could not verify payment.", show_alert=True)


async def send_files(client: Client, message: Message, base64_string: str):
    try:
        _string = await decode(base64_string)
        argument = _string.split("-")

        if len(argument) == 3:
            start = int(int(argument[1]) / abs(client.db_channel.id))
            end = int(int(argument[2]) / abs(client.db_channel.id))
            ids = list(range(start, end + 1)) if start <= end else list(range(start, end - 1, -1))
        else:
            ids = [int(int(argument[1]) / abs(client.db_channel.id))]

        temp_msg = await message.reply("Please wait...")
        messages = await get_messages(client, ids)
        await temp_msg.delete()

        for msg in messages:
            caption = (
                CUSTOM_CAPTION.format(
                    previouscaption="" if not msg.caption else msg.caption.html,
                    filename=msg.document.file_name
                ) if bool(CUSTOM_CAPTION) and bool(msg.document) else
                "" if not msg.caption else msg.caption.html
            )

            reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None

            try:
                await msg.copy(
                    chat_id=message.chat.id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    protect_content=PROTECT_CONTENT
                )
                await asyncio.sleep(0.5)
            except FloodWait as e:
                await asyncio.sleep(e.x)
            except:
                pass
    except Exception as e:
        logging.error(str(e))
        await message.reply_text("Something went wrong while sending files.")
