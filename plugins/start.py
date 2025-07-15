#(©)CodeXBotz
import asyncio
import base64
import logging
import os
import random
import re
import string
import time

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

import razorpay
from bot import Bot
from config import (
    ADMINS,
    FORCE_MSG,
    START_MSG,
    CUSTOM_CAPTION,
    IS_VERIFY,
    VERIFY_EXPIRE,
    DISABLE_CHANNEL_BUTTON,
    PROTECT_CONTENT,
    TUT_VID,
    OWNER_ID,
)
from helper_func import (
    subscribed,
    encode,
    decode,
    get_messages,
)
from database.database import add_user, del_user, full_userbase, present_user

# Razorpay Setup
razorpay_client = razorpay.Client(auth=("rzp_live_Kfvz8iobE8iUZc", "bcPhJQ2pHTaaF94FhWCEl6eD"))
PAYMENT_AMOUNT = 2  # Rs. 2
PAYMENT_CURRENCY = "INR"

Bot.batch_data = {}

@Bot.on_message(filters.command("start") & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    id = message.from_user.id
    owner_id = ADMINS

    if id == owner_id:
        await message.reply("You are the owner! Additional actions can be added here.")
        return

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

        order_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        payment = razorpay_client.payment_link.create({
            "amount": PAYMENT_AMOUNT * 100,
            "currency": PAYMENT_CURRENCY,
            "description": f"Batch files access – {id}",
            "reference_id": order_id,
            "customer": {"name": message.from_user.first_name},
            "notify": {"sms": False, "email": False},
            "reminder_enable": True
        })

        link_id = payment["id"]
        short_url = payment["short_url"]
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={short_url}"

        Bot.batch_data[id] = {"link_id": link_id, "ids": ids}

        await message.reply_photo(
            photo=qr_url,
            caption=f"Please pay ₹2 to access your files.\n[Pay Now]({short_url})",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("I've Paid ✅", callback_data=f"checkpay_{id}")]
            ])
        )
        return

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


@Bot.on_callback_query(filters.regex("checkpay_(.*)"))
async def check_payment_callback(client, callback_query: CallbackQuery):
    user_id = int(callback_query.data.split("_", 1)[1])
    data = Bot.batch_data.get(user_id)
    if not data:
        return await callback_query.message.edit("Session expired or invalid.")

    link = razorpay_client.payment_link.fetch(data["link_id"])
    if link["status"] == "paid":
        temp_msg = await callback_query.message.edit("Payment successful! Sending files...")
        messages = await get_messages(client, data["ids"])
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
                    chat_id=callback_query.from_user.id,
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
        Bot.batch_data.pop(user_id, None)
        return
    else:
        await callback_query.answer("Payment not received yet. Please wait a moment and try again.", show_alert=True)


@Bot.on_message(filters.command("start") & filters.private)
async def not_joined(client: Client, message: Message):
    buttons = [
        [
            InlineKeyboardButton("Join Channel", url=client.invitelink),
            InlineKeyboardButton("Join Channel", url=client.invitelink2),
        ]
    ]
    try:
        buttons.append([
            InlineKeyboardButton("Try Again", url=f"https://t.me/{client.username}?start={message.command[1]}")
        ])
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
        msg = await message.reply(
            "<code>Use this command as a reply to any Telegram message without any spaces.</code>"
        )
        await asyncio.sleep(8)
        await msg.delete()
