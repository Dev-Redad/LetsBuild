#(©)CodeXBotz
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

# Razorpay client
client_rzp = razorpay.Client(auth=("rzp_live_Kfvz8iobE8iUZc", "bcPhJQ2pHTaaF94FhWCEl6eD"))
PAYMENT_AMOUNT = 2  # INR
PAYMENT_CURRENCY = "INR"

payment_status = {}

@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    id = message.from_user.id

    if id in ADMINS:
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

        if id in payment_status and payment_status[id].get("paid"):
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

            temp_msg = await message.reply("Please wait...")
            try:
                messages = await get_messages(client, ids)
            except:
                await message.reply_text("Something went wrong..!")
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
                        chat_id=message.from_user.id,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup,
                        protect_content=PROTECT_CONTENT
                    )
                    await asyncio.sleep(0.5)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    await msg.copy(
                        chat_id=message.from_user.id,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup,
                        protect_content=PROTECT_CONTENT
                    )
                except:
                    pass
        else:
            order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            payment_link = client_rzp.payment_link.create({
                "amount": PAYMENT_AMOUNT * 100,
                "currency": PAYMENT_CURRENCY,
                "description": f"Batch files permission – {id}",
                "reference_id": order_id,
                "customer": {"name": message.from_user.first_name},
                "notify": {"sms": False, "email": False},
                "reminder_enable": True
            })
            link_id = payment_link["id"]
            pay_url = payment_link["short_url"]
            payment_status[id] = {"link_id": link_id, "paid": False, "payload": base64_string}

            buttons = [
                [InlineKeyboardButton("Pay ₹2", url=pay_url)],
                [InlineKeyboardButton("I’ve Paid", callback_data=f"checkpay_{id}")]
            ]
            await message.reply("Please complete payment to receive the batch files:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("About Me", callback_data="about"), InlineKeyboardButton("Close", callback_data="close")]
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

@Bot.on_callback_query(filters.regex("^checkpay_"))
async def check_payment(client, callback_query: CallbackQuery):
    id = int(callback_query.data.split("_", 1)[1])
    user_data = payment_status.get(id)
    if not user_data:
        return await callback_query.answer("No payment initiated.", show_alert=True)

    link_id = user_data["link_id"]
    pl = client_rzp.payment_link.fetch(link_id)
    if pl["status"] == "paid":
        payment_status[id]["paid"] = True
        return await callback_query.message.reply("✅ Payment confirmed. Please click /start again to receive files.")
    else:
        return await callback_query.answer("Payment not yet completed.", show_alert=True)

@Bot.on_message(filters.command('start') & filters.private)
async def not_joined(client: Client, message: Message):
    buttons = [
        [InlineKeyboardButton("Join Channel", url=client.invitelink), InlineKeyboardButton("Join Channel", url=client.invitelink2)]
    ]
    try:
        buttons.append([InlineKeyboardButton("Try Again", url=f"https://t.me/{client.username}?start={message.command[1]}")])
    except IndexError:
        pass

    await message.reply(
        text=FORCE_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=None if not message.from_user.username else '@' + message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id
        ),
        reply_markup=InlineKeyboardMarkup(buttons),
        quote=True,
        disable_web_page_preview=True
    )

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
        msg = await message.reply("<code>Use this command as a reply to any Telegram message without any spaces.</code>")
        await asyncio.sleep(8)
        await msg.delete()
