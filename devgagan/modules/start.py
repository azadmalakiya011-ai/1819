import datetime, asyncio
from pyrogram import filters, StopPropagation
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message, BotCommand
from devgagan import app
from config import OWNER_ID
from devgagan.core.func import subscribe, chk_user
from devgagan.core.mongo.db import db
from devgagan.core.mongo.plans_db import premium_users

users_collection = db["users"]
plans_collection = db["plans"]
tokens_collection = db["tokens"]

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message: Message):
    if len(message.command) > 1:
        return
    await message.reply_text(
        f"👋 **નમસ્તે {message.from_user.first_name}!**\n\n"
        "હું Save Restricted Content Bot છું.\n"
        "કોઈ પણ લિંક મોકલીને ડાઉનલોડ શરૂ કરો અથવા મદદ માટે /help વાપરો."
    )

@app.on_message(filters.command("set"))
async def set(_, message):
    if message.from_user.id not in OWNER_ID:
        return await message.reply("You are not authorized.")
    await app.set_bot_commands([
        BotCommand("start", "🚀 Start"), BotCommand("batch", "🫠 Extract bulk"), BotCommand("login", "🔑 Login"),
        BotCommand("logout", "🚪 Logout"), BotCommand("token", "🎲 Free access"),
        BotCommand("myplan", "⌛ Plan details"), BotCommand("plans", "🗓️ Premium plans"), BotCommand("help", "❓ Help"),
        BotCommand("cancel", "🚫 Cancel process"), BotCommand("settings", "⚙️ Settings")
    ])
    await message.reply("✅ Commands configured successfully!")

@app.on_message(filters.command("help"))
async def help(client, message):
    if await subscribe(client, message) == 1:
        return
    await message.reply("📝 **Bot Commands:**\n/batch - Bulk download\n/login - Login account\n/token - Get session\n/myplan - Check plan")

@app.on_message(filters.command("terms") & filters.private)
async def terms(client, message):
    await message.reply_text("📜 **Terms and Conditions:** We do not promote copyrighted content. Use at your own risk.")

@app.on_message(filters.command("plans") & filters.private)
async def plan(client, message):
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("💬 Contact Owner", url="https://t.me/TEAM_AxxxS_BOT")]])
    await message.reply_text("💎 **Premium Plans**\n\n🔹 Free: Limited\n🔟 7 Days: ₹30\n🌀 15 Days: ₹60\n🏆 30 Days: ₹90\n\nContact @TEAM_AxxxS_BOT to buy.", reply_markup=btn)

@app.on_message(filters.command("guide"))
async def guide_command(_, message: Message):
    await message.reply_photo("https://i.postimg.cc/BXkchVpY/image.jpg", caption="📘 **Guide:**\n1. મોકલો પબ્લિક લિંક ડાઉનલોડ કરવા.\n2. પ્રાઈવેટ માટે /login વાપરો.\n3. /batch થી વધારે ફાઈલો ડાઉનલોડ થશે.")
    
