# ---------------------------------------------------
# File Name: shrink.py
# Description: A Pyrogram bot for downloading files from Telegram channels or groups 
#              and uploading them back to Telegram.
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# Telegram: https://t.me/team_spy_pro
# YouTube: https://youtube.com/@dev_gagan
# Created: 2025-01-11
# Last Modified: 2025-01-11
# Version: 2.0.5
# License: MIT License
# ---------------------------------------------------

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
import os
import random
import requests
import string
import aiohttp
from devgagan import app
from devgagan.core.func import *
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_DB, WEBSITE_URL, AD_API, LOG_GROUP  

# Koyeb માંથી TOKEN_TIMEOUT લેશે (જો ન મળે તો બાય-ડિફોલ્ટ 10800 એટલે કે 3 કલાક)
try:
    from config import TOKEN_TIMEOUT
    TOKEN_TIMEOUT = int(TOKEN_TIMEOUT)
except Exception:
    TOKEN_TIMEOUT = int(os.environ.get("TOKEN_TIMEOUT", 10800))

tclient = AsyncIOMotorClient(MONGO_DB)
tdb = tclient["telegram_bot"]
token = tdb["tokens"]
token_cooldown = tdb["token_cooldown"]
 
 
async def create_ttl_index():
    await token.create_index("expires_at", expireAfterSeconds=0)
    await token_cooldown.create_index("expires_at", expireAfterSeconds=0)
 
 
Param = {}
 
 
async def generate_random_param(length=8):
    """Generate a random parameter."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
 
 
async def get_shortened_url(deep_link):
    api_url = f"https://{WEBSITE_URL}/api?api={AD_API}&url={deep_link}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()   
                    if data.get("status") == "success":
                        return data.get("shortenedUrl")
    except Exception as e:
        print(f"[!] Shortener error: {e}")
    return None
 
 
async def is_user_verified(user_id):
    """Check if a user has an active session."""
    session = await token.find_one({"user_id": user_id})
    return session is not None


# 🪙 /token command handler
@app.on_message(filters.command("token") & filters.private)
async def token_command_handler(client: Client, message: Message):
    user_id = message.chat.id
    
    # Check if user is premium
    freecheck = await chk_user(message, user_id)
    if freecheck != 1:
        await message.reply("👑 You are a Premium User! You do not need any token.")
        return
        
    # Check if already verified (Active 3-hour session)
    if await is_user_verified(user_id):
        await message.reply("✅ You already have an active token session! Enjoy unlimited access.")
        return

    # ૨૪ કલાકનું કુલડાઉન ચેક
    now = datetime.utcnow()
    cooldown = await token_cooldown.find_one({"user_id": user_id})
    if cooldown:
        exp_time = cooldown.get("expires_at")
        if exp_time and exp_time > now:
            time_left = exp_time - now
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            await message.reply(
                f"⚠️ **લિમિટ પૂરી થઈ ગઈ છે!**\n\n"
                f"તમે ૨૪ કલાકમાં ફક્ત ૧ જ વાર ટોકન લઈ શકો છો.\n"
                f"⏳ ફરી ટોકન લેવા માટે બાકી સમય: `{hours} કલાક, {minutes} મિનિટ`.\n\n"
                f"અનલિમિટેડ વાપરવા માટે પ્રીમિયમ ખરીદો: /plans"
            )
            return
        else:
            await token_cooldown.delete_one({"user_id": user_id})

    msg = await message.reply("⏳ **Generating your token link, please wait...**")
    
    param = await generate_random_param()
    Param[user_id] = param
    
    bot = await client.get_me()
    deep_link = f"https://t.me/{bot.username}?start={param}"
    
    short_link = await get_shortened_url(deep_link)
    
    if not short_link:
        await msg.edit("❌ **Error generating token link.** Please check shortener API or try again later.")
        return

    button = InlineKeyboardMarkup([
        [InlineKeyboardButton("👉 Get Token 👈", url=short_link)],
        [InlineKeyboardButton("💡 How to Open Link?", url="https://t.me/SRC_PRO")]
    ])
    
    caption = (
        "🔐 **Token Verification Required**\n\n"
        "To get 3 hours of unlimited downloads without any delay:\n\n"
        "1️⃣ Click the button below to open the link.\n"
        "2️⃣ Complete the shortener steps.\n"
        "3️⃣ You will be redirected back to this bot automatically!\n\n"
        "⏱️ **Validity:** 3 Hours\n"
        "⚠️ **નોંધ:** ૨૪ કલાકમાં ફક્ત ૧ જ વાર ટોકન મળશે."
    )
    
    await msg.edit(caption, reply_markup=button)


@app.on_message(filters.command("start"))
async def token_handler(client, message):
    """Handle the /start command."""
    # જો લિંકમાં રેફરલ (ref_) હોય તો ટોકન સિસ્ટમ તરત અટકી જશે
    if len(message.command) > 1 and str(message.command[1]).startswith("ref_"):
        return

    join = await subscribe(client, message)
    if join == 1:
        return

    chat_id = "save_restricted_content_bots"
    msg = await app.get_messages(chat_id, 796)
    user_id = message.chat.id

    if len(message.command) <= 1:
        image_url = "https://freeimage.host/i/F5dGOsj"
        join_button = InlineKeyboardButton("✈️ Main Channel", url="https://t.me/SRC_PRO")
        premium = InlineKeyboardButton("🦋 Contact Owner", url="https://t.me/TEAM_AxxxS_BOT")
        keyboard = InlineKeyboardMarkup([
            [join_button],
            [premium]
        ])

        user_mention = message.from_user.mention if message.from_user else "User"

        await message.reply_photo(
            image_url,            
            caption=(
                f"👋 **Hello, {user_mention}! Welcome to Save Restricted Bot!**\n\n"
                "🔒 I Can Help You To **Save And Forward Content** from channels or groups that don't allow forwarding.🤫\n\n"
                "📌 **How to use me:**\n"
                "➤ Just **send me the post link** if it's Public\n"
                "🔓 I'll send that post(s) to you.\n\n"
                "> 💠 Use /batch For Bulk Forwarding...💀\n"
                "🔐 **Private channel post?**\n\n"                
                "➤ First do /login to save posts from Private Channel\n\n"
                "💎 **Get Premium /plans**\n"
                "💡 Need help? Send /guide\n For More Features Use /settings 😉 \n\n"
                ">⚡ Contact Owner: @TEAM_AxxxS_BOT"
            ),
            reply_markup=keyboard,
            message_effect_id=5104841245755180586
        )
        return
 
    param = message.command[1] if len(message.command) > 1 else None
    
    # જો કોઈ પણ રીતે પેરામીટર ref_ હોય તો લાલ એરર મોકલ્યા વગર સીધા બહાર નીકળી જવું
    if param and str(param).startswith("ref_"):
        return

    freecheck = await chk_user(message, user_id)
    if freecheck != 1:
        await message.reply("You are a premium user Cutie 😉\n\n Just /start & Use Me  🫠")
        return
 
    if param:
        if user_id in Param and Param[user_id] == param:
            now = datetime.utcnow()
            
            # Koyeb ના TOKEN_TIMEOUT મુજબ વેલિડિટી (3 કલાક)
            await token.insert_one({
                "user_id": user_id,
                "param": param,
                "created_at": now,
                "expires_at": now + timedelta(seconds=TOKEN_TIMEOUT),
            })
            
            # 24 કલાક માટે નવો ટોકન લેવા પર લોક
            await token_cooldown.update_one(
                {"user_id": user_id},
                {"$set": {
                    "user_id": user_id,
                    "verified_at": now,
                    "expires_at": now + timedelta(hours=24)
                }},
                upsert=True
            )
            
            del Param[user_id]   
            await message.reply("✅ You have been verified successfully! Enjoy your session for next 3 hours.")
            return
        else:
            # રેફરલ લિંક ન હોય અને માત્ર ખોટો ટોકન હોય ત્યારે જ લાલ એરર આવશે
            if not str(param).startswith("ref_"):
                await message.reply("❌ Invalid or expired verification link. Please generate a new token.")       
            return


# 🔗 /sharelink command
@app.on_message(filters.command("shareme"))
async def sharelink_handler(client, message: Message):
    bot = await client.get_me()
    bot_username = bot.username

    bot_link = f"https://t.me/{bot_username}?start=True"
    share_link = f"https://t.me/share/url?url={bot_link}&text=🚀%20Check%20out%20this%20awesome%20bot%20to%20unlock%20restricted%20Telegram%20content!%20Try%20now%20"

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Share Me With Others 🫠", url=share_link)]
    ])

    await message.reply_text(
        f"✨ **Spread the Magic!**\n\n"
        f"Help others discover this bot that can save **restricted channel media**, even if forwarding is off! 🔒\n\n"
        f"Click a button below 👇 share me with your friends!",
        reply_markup=reply_markup
    )
    
