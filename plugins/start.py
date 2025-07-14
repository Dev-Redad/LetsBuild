# Updated start.py with Razorpay payment integration per batch
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
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait

from bot import Bot
from config import (
    ADMINS, FORCE_MSG, START_MSG, CUSTOM_CAPTION, IS_VERIFY,
    DISABLE_CHANNEL_BUTTON, PROTECT_CONTENT, OWNER_ID
)
from helper_func import (
    subscribed, encode, decode, get_messages
)
from database.database import add_user, del_user, full_userbase, present_user

# Razorpay credentials
RAZORPAY_KEY_ID = "rzp_live_Kfvz8iobE8iUZc"
RAZORPAY_KEY_SECRET = "bcPhJQ2pHTaaF94FhWCEl6eD"
client_razorpay = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# In-memory tracking (can be replaced with a database)
paid_users = {}

@Bot.on_message(filters.command("start") & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    id = message.from_user.id

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
                ids = list(range(start, end + 1)) if start <= end else list(range(start, end - 1, -1))
            except:
                return
        elif len(argument) == 2:
            try:
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]
            except:
                return
        else:
            return

        # Payment check
        if paid_users.get((id, tuple(ids))):
            await send_files(client, message, ids)
            return

        # Create Razorpay order
        try:
            payment_order = client_razorpay.order.create({
                "amount": 200,  # in paise = ₹2.00
                "currency": "INR",
                "payment_capture": 1,
                "notes": {"user_id": str(id)}
            })

            pay_url = f"https://rzp.io/l/{payment_order['id']}"
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("Pay ₹2 to Access Files", url=pay_url)],
                [InlineKeyboardButton("I've Paid", callback_data=f"verify_{payment_order['id']}")]
            ])

            await message.reply(
                "To access this batch, please pay ₹2.",
                reply_markup=markup
            )

            # Track request
            paid_users[(id, tuple(ids))] = {"order_id": payment_order['id'], "paid": False, "ids": ids}
        except Exception as e:
            await message.reply("Payment gateway error. Please try again later.")
            logging.error(str(e))

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

@Bot.on_callback_query(filters.regex("^verify_"))
async def verify_payment(client: Client, query):
    user_id = query.from_user.id
    order_id = query.data.split("_", 1)[1]

    # Find the matching request
    for key, value in paid_users.items():
        if key[0] == user_id and value['order_id'] == order_id:
            try:
                payments = client_razorpay.order.payments(order_id)
                for p in payments['items']:
                    if p['status'] == 'captured':
                        value['paid'] = True
                        await query.message.edit("Payment received! Here's your batch...")
                        await send_files(client, query.message, value['ids'])
                        return
                await query.answer("Payment not yet received. Please wait.", show_alert=True)
            except Exception as e:
                await query.answer("Verification error.", show_alert=True)
            break


async def send_files(client, message, ids):
    temp_msg = await message.reply("Preparing your files...")
    try:
        messages = await get_messages(client, ids)
    except:
        await temp_msg.edit("Something went wrong!")
        return
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
            await msg.copy(
                chat_id=message.chat.id,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                protect_content=PROTECT_CONTENT
            )
        except:
            pass
