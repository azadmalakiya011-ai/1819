# ---------------------------------------------------
# File Name: start.py
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

import datetime
from pyrogram import filters
from devgagan import app
from config import OWNER_ID
from devgagan.core.func import subscribe
import asyncio
from devgagan.core.func import *
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message, BotCommand
from pyrogram.raw.functions.bots import SetBotInfo
from pyrogram.raw.types import InputUserSelf
from devgagan.core.mongo.db import db
from devgagan.core.mongo.users_db import add_premium

# Database Collections
referral_collection = db["referrals"]
users_collection = db["users"]

# --- DATABASE FUNCTIONS FOR REFERRAL ---
async def get_referral_data(user_id: int):
    data = await referral_collection.find_one({"user_id": user_id})
    if not data:
        data = {"user_id": user_id, "referrals": 0, "redeemed": 0}
        await referral_collection.insert_one(data)
    return data

async def add_referral(referrer_id: int, new_user_id: int):
    user_exists = await users_collection.find_one({"user_id": new_user_id})
    ref_exists = await referral_collection.find_one({"user_id": new_user_id})
    if user_exists or ref_exists:
        return False

    await referral_collection.insert_one({"user_id": new_user_id, "referrals": 0, "redeemed": 0})
    await referral_collection.update_one(
        {"user_id": referrer_id},
        {"$inc": {"referrals": 1}},
        upsert=True
    )
    return True

async def redeem_referral_points(user_id: int):
    data = await get_referral_data(user_id)
    total_refs = data.get("referrals", 0)
    redeemed = data.get("redeemed", 0)
    
    available_points = total_refs - (redeemed * 3)
    if available_points >= 3:
        await referral_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"redeemed": 1}}
        )
        return True
    return False

# --- REFERRAL START HANDLER (TOKEN ERROR PREVENTER) ---
@app.on_message(filters.command("start") & filters.private, group=-100)
async def ref_start_handler(client, message: Message):
    if len(message.command) > 1 and message.command[1].startswith("ref_"):
        try:
            referrer_id = int(message.command[1].replace("ref_", ""))
            new_user_id = message.from_user.id

            if referrer_id == new_user_id:
                await message.reply_text("❌ તમે તમારી પોતાની લિંક વાપરી શકતા નથી!")
                message.stop_propagation()
                return

            success = await add_referral(referrer_id, new_user_id)
            if success:
                try:
                    await client.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 **નવો રેફરલ જોડાયો!**\n\nયુઝર: {message.from_user.mention} તમારી લિંકથી સફળતાપૂર્વક જોડાયા છે."
                    )
                except Exception:
                    pass
                await message.reply_text(
                    f"👋 **નમસ્તે {message.from_user.first_name}!**\n\n"
                    "🎉 તમે સફળતાપૂર્વક રેફરલ લિંક દ્વારા બોટમાં જોડાઈ ગયા છો.\n\n"
                    "👉 બોટનો ઉપયોગ કરવા માટે /token મેળવી લો અથવા તમારા મિત્રોને /referral દ્વારા જોડીને Pro પ્લાન મેળવો!"
                )
            else:
                await message.reply_text(
                    f"👋 **નમસ્તે {message.from_user.first_name}!**\n\n"
                    "⚠️ તમે પહેલેથી જ બોટના સભ્ય છો, તેથી રેફરલ ગણાયો નથી.\n\n"
                    "👉 બોટ વાપરવા માટે /token મેળવી લો અથવા તમારા મિત્રોને /referral થી જોડી Pro પ્લાન મેળવો!"
                )
            
            message.stop_propagation()
            return
        except Exception:
            pass


@app.on_message(filters.command("set"))
async def set(_, message):
    if message.from_user.id not in OWNER_ID:
        await message.reply("You are not authorized to use this command.")
        return
     
    await app.set_bot_commands([
        BotCommand("start", "🚀 Start the bot"),
        BotCommand("batch", "🫠 Extract in bulk"),
        BotCommand("login", "🔑 Get into the bot"),
        BotCommand("logout", "🚪 Get out of the bot"),
        BotCommand("token", "🎲 Get 3 hours free access"),
        BotCommand("referral", "🎁 Invite friends and get Pro"),
        BotCommand("adl", "👻 Download audio from 30+ sites"),
        BotCommand("dl", "💀 Download videos from 30+ sites"),
        BotCommand("freez", "🧊 Remove all expired user"),
        BotCommand("pay", "₹ Pay now to get subscription"),
        BotCommand("status", "⟳ Refresh Payment status"),
        BotCommand("transfer", "💘 Gift premium to others"),
        BotCommand("myplan", "⌛ Get your plan details"),
        BotCommand("add", "➕ Add user to premium"),
        BotCommand("rem", "➖ Remove from premium"),
        BotCommand("session", "🧵 Generate Pyrogramv2 session"),
        BotCommand("settings", "⚙️ Personalize things"),
        BotCommand("stats", "📊 Get stats of the bot"),
        BotCommand("plan", "🗓️ Check our premium plans"),
        BotCommand("terms", "🥺 Terms and conditions"),
        BotCommand("speedtest", "🚅 Speed of server"),
        BotCommand("lock", "🔒 Protect channel from extraction"),
        BotCommand("gcast", "⚡ Broadcast message to bot users"),
        BotCommand("help", "❓ If you're a noob, still!"),
        BotCommand("cancel", "🚫 Cancel batch process")
    ])
 
    await message.reply("✅ Commands configured successfully!")
 
 
help_pages = [
    (
        "📝 **Bot Commands Overview (1/2)**:\n\n"
        "💠 **/id To Get id**\n"
        "> Use This Command To Get Your id & Add Me in you Channel/Groups To Get That Chat id \n\n"
        "1. **/add userID**\n"
        "> Add user to premium (Owner only)\n\n"
        "2. **/rem userID**\n"
        "> Remove user from premium (Owner only)\n\n"
        "3. **/transfer userID**\n"
        "> Transfer premium to your beloved major purpose for resellers (Premium members only)\n\n"
        "4. **/get**\n"
        "> Get all user IDs (Owner only)\n\n"
        "5. **/lock**\n"
        "> Lock channel from extraction (Owner only)\n\n"
        "6. **/dl link**\n"
        "> Download videos (Not available in v3 if you are using)\n\n"
        "7. **/adl link**\n"
        "> Download audio (Not available in v3 if you are using)\n\n"
        "8. **/login**\n"
        "> Log into the bot for private channel access\n\n"
        "9. **/batch**\n"
        "> Bulk extraction for posts (After login)\n\n"
    ),
    (
        "📝 **Bot Commands Overview (2/2)**:\n\n"
        "10. **/logout**\n"
        "> Logout from the bot\n\n"
        "11. **/stats**\n"
        "> Get bot stats\n\n"
        "12. **/plan**\n"
        "> Check premium plans\n\n"
        "13. **/speedtest**\n"
        "> Test the server speed (not available in v3)\n\n"
        "14. **/terms**\n"
        "> Terms and conditions\n\n"
        "15. **/cancel**\n"
        "> Cancel ongoing batch process\n\n"
        "16. **/myplan**\n"
        "> Get details about your plans\n\n"
        "17. **/session**\n"
        "> Generate Pyrogram V2 session\n\n"
        "18. **/settings**\n"
        "> 1. SETCHATID : To directly upload in channel or group or user's dm use it with -100[chatID]\n"
        "> 2. SETRENAME : To add custom rename tag or username of your channels\n"
        "> 3. CAPTION : To add custom caption\n"
        "> 4. REPLACEWORDS : Can be used for words in deleted set via REMOVE WORDS\n"
        "> 5. RESET : To set the things back to default\n\n"
        "> You can set CUSTOM THUMBNAIL, PDF WATERMARK, VIDEO WATERMARK, SESSION-based login, etc. from settings\n\n"
        "**__Powered By ╰‿╯ ҡσℓเ ⚝__**"
    )
]
 
async def send_or_edit_help_page(_, message, page_number):
    if page_number < 0 or page_number >= len(help_pages):
        return
     
    prev_button = InlineKeyboardButton("◀️ Previous", callback_data=f"help_prev_{page_number}")
    next_button = InlineKeyboardButton("Next ▶️", callback_data=f"help_next_{page_number}")
     
    buttons = []
    if page_number > 0:
        buttons.append(prev_button)
    if page_number < len(help_pages) - 1:
        buttons.append(next_button)
     
    keyboard = InlineKeyboardMarkup([buttons])
     
    await message.delete()
     
    await message.reply(
        help_pages[page_number],
        reply_markup=keyboard
    )
 
@app.on_message(filters.command("help"))
async def help(client, message):
    join = await subscribe(client, message)
    if join == 1:
        return
     
    await send_or_edit_help_page(client, message, 0)
 
@app.on_callback_query(filters.regex(r"help_(prev|next)_(\d+)"))
async def on_help_navigation(client, callback_query):
    action, page_number = callback_query.data.split("_")[1], int(callback_query.data.split("_")[2])
 
    if action == "prev":
        page_number -= 1
    elif action == "next":
        page_number += 1
     
    await send_or_edit_help_page(client, callback_query.message, page_number)
    await callback_query.answer()
 
@app.on_message(filters.command("terms") & filters.private)
async def terms(client, message):
    terms_text = (
        "> 📜 **Terms and Conditions** 📜\n\n"
        "✨ We are not responsible for user deeds, and we do not promote copyrighted content. If any user engages in such activities, it is solely their responsibility.\n"
        "✨ Upon purchase, we do not guarantee the uptime, downtime, or the validity of the plan. __Authorization and banning of users are at our discretion; we reserve the right to ban or authorize users at any time.__\n"
        "✨ Payment to us **__does not guarantee__** authorization for the /batch command. All decisions regarding authorization are made at our discretion and mood.\n"
    )
     
    buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📋 See Plans", callback_data="see_plan")],
            [InlineKeyboardButton("💬 Contact Now", url="https://t.me/TEAM_AxxxS_BOT")],
        ]
    )
    await message.reply_text(terms_text, reply_markup=buttons)
 
@app.on_message(filters.command("plans") & filters.private)
async def plan(client, message):
    plan_text = (
        "💎 **Upgrade to Premium** 💎\n\n"
        "🚀 **Premium Features**\n"
        "✅ No verification every 2 hours ⏳\n"
        "✅ Upload in bulk (up to 2000 files) 📂\n"
        "✅ Instantly skip the 300-second wait ⏱️\n"
        "✅ Extract unlimited videos from channels, groups, and bots 🎥\n\n"
        "🔹 **Free Plan**\n"
        "⏳ Validity: Unlimited\n"
        "💰 Price: ₹0 / $0.00 USDT\n"
        "❌ Limited features\n"
        "❌ Limited downloads\n\n"
        "🔟 **7-Day Plan**\n"
        "💰 Price: ₹30 / $0.50 USDT\n"
        "⏳ Validity: 7 days\n"
        "🎥 Extract unlimited videos\n\n"
        "🌀 **15-Day Plan**\n"
        "💰 Price: ₹60 / $0.90 USDT\n"
        "⏳ Validity: 15 days\n"
        "🎥 Extract unlimited videos\n\n"
        "🏆 **Monthly Plan**\n"
        "💰 Price: ₹90 / $1.20 USDT\n"
        "⏳ Validity: 30 days\n"
        "🎥 Extract unlimited videos\n"
        "⚡ High Speed 🚀\n"
        "═══════════════════\n"
        "💰 Better Plans Then others 💯\n\n"
        "📲 To Upgrade: Contact @TEAM_AxxxS_BOT\n\n"
        "💳 Payment via UPI, Amazon Gift Card or USDT\n"
    )
     
    buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📜 See Terms", callback_data="see_terms")],
            [InlineKeyboardButton("💬 Contact Now", url="https://t.me/TEAM_AxxxS_BOT")],
        ]
    )
    await message.reply_text(plan_text, reply_markup=buttons)
 
@app.on_callback_query(filters.regex("see_plan"))
async def see_plan(client, callback_query):
    plan_text = (
        "> 💰**Premium Price**\n\n Starting from $2 or 200 INR accepted via **__Amazon Gift Card__** (terms and conditions apply).\n"
        "📥 **Download Limit**: Users can download up to 100,000 files in a single batch command.\n"
        "🛑 **Batch**: You will get two modes /bulk and /batch.\n"
        "   - Users are advised to wait for the process to automatically cancel before proceeding with any downloads or uploads.\n\n"
        "📜 **Terms and Conditions**: For further details and complete terms and conditions, please send /terms or click See Terms👇\n"
    )
     
    buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📜 See Terms", callback_data="see_terms")],
            [InlineKeyboardButton("💬 Contact Now", url="https://t.me/TEAM_AxxxS_BOT")],
        ]
    )
    await callback_query.message.edit_text(plan_text, reply_markup=buttons)
 
@app.on_callback_query(filters.regex("see_terms"))
async def see_terms(client, callback_query):
    terms_text = (
        "> 📜 **Terms and Conditions** 📜\n\n"
        "✨ We are not responsible for user deeds, and we do not promote copyrighted content. If any user engages in such activities, it is solely their responsibility.\n"
        "✨ Upon purchase, we do not guarantee the uptime, downtime, or the validity of the plan. __Authorization and banning of users are at our discretion; we reserve the right to ban or authorize users at any time.__\n"
        "✨ Payment to us **__does not guarantee__** authorization for the /batch command. All decisions regarding authorization are made at our discretion and mood.\n"
    )
     
    buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📋 See Plans", callback_data="see_plan")],
            [InlineKeyboardButton("💬 Contact Now", url="https://t.me/@TEAM_AxxxS_BOT")],
        ]
    )
    await callback_query.message.edit_text(terms_text, reply_markup=buttons)

@app.on_message(filters.command("guide"))
async def guide_command(_, message: Message):
    image_url = "https://i.postimg.cc/BXkchVpY/image.jpg"
    await message.reply_photo(
        photo=image_url,
        caption=(
            "📘 **How to Use Save Restricted Bot**\n\n"
            "If you want to Download Posts From Public Channels/Groups Just Send me **Post Link**\n"        
            "🔓 I'll unlock content from restricted channels or groups.\n\n"
            "Use /settings for Settings 🌝\n\n"
            "Use Next Button For Private Channels/Groups Guide 👇"
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➡️ Next", callback_data="guide_page_1")]
        ]),
        quote=True
    )

@app.on_callback_query(filters.regex("^guide_page_2$"))
async def guide_page_2(_, query: CallbackQuery):
    await query.message.edit_text(
        "🛠️ **More Features 😎**\n\n"
        "✅ Supported post formats:\n\n"
        "Public Link:\n `https://t.me/public_channel/1234`\n\n"
        "Private Link:\n `https://t.me/c/123456789/55`\n\n"
        "💡 Use /login only for private source.\n"
        "Use /id to get user or chat ID.\n\n"
        "Use /batch to download multiple posts at once 💀\n\n"
        "Powered by ╰‿╯ ҡσℓเ ⚝",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data="guide_page_1")]
        ])
    )

@app.on_callback_query(filters.regex("^guide_page_1$"))
async def guide_page_1(_, query: CallbackQuery):
    await query.message.edit_text(
        "**📘 How to Use @SRC_PRO_BOT Guide 👇**\n\n"
        "💡 **For Private Channels/Groups**\n\n"
        "**How to download or forward posts from Private Channel/Groups Where Save is Restricted 💀**\n"
        "────────────────────\n"
        "➡️ Send /start\n"
        "➡️ Send /login\n"
        "────────────────────\n"
        "**Now 📲 Enter your mobile number\n like:**\n"
        "`+91XXXXXXXXXX`\n\n"
        "📨 You’ll get an OTP from Telegram official chat.\n"
        "────────────────────\n"
        "**🔢 Enter the OTP with spaces between digits.**\n"
        "Example: If OTP is `54321`,\n enter: `5 4 3 2 1`\n\n"
        "✅ You’ll be logged in successfully!\n"
        "────────────────────\n"
        "⚡ Now use /batch to download multiple posts.\n"
        "▭▭▭▭▭▭▭▭▭▭▭▭▭▭▭\n\n"
        "**हिंदी में 👇**\n\n"
        "**@SRC_PRO_BOT** का कैसे उपयोग करें\n"
        "/start कमांड भेजें फिर\n"
        "/login कमांड भेजें\n"
        "────────────────────\n"
        "📲 अब अपना मोबाइल नंबर दर्ज करें:\n"
        "`+91XXXXXXXXXX`\n\n"
        "────────────────────\n"
        "📨 Telegram की official चैट से OTP आएगा\n"     
        "🔢 OTP को स्पेस के साथ दर्ज करें\n"
        "उदाहरण: 5 4 3 2 1\n\n"
        "✅ अब आप सफलतापूर्वक बॉट में लॉग इन हो जाएंगे\n"
        "────────────────────\n"
        "⚡ एक बार में कई पोस्ट डाउनलोड करने के लिए /batch का उपयोग करें।"
        "▭▭▭▭▭▭▭▭▭▭▭▭▭▭▭\n\n",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("More Features 😎", callback_data="guide_page_2")]
        ])
    )

# --- REFERRAL COMMAND MENU ---
@app.on_message(filters.command("referral") & filters.private)
async def referral_menu(client, message):
    user_id = message.from_user.id
    bot_username = (await client.get_me()).username
    data = await get_referral_data(user_id)

    total_refs = data.get("referrals", 0)
    redeemed = data.get("redeemed", 0)
    can_redeem = (total_refs - (redeemed * 3)) // 3

    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    text = (
        f"👑 **{message.from_user.first_name}**\n"
        f"`/referral`\n"
        f"🎁 **Referral Program**\n\n"
        f"_Invite friends and earn Pro!_\n"
        f"_Every 3 referrals = 3 Hours Pro_\n\n"
        f"**Your Referrals:** {total_refs}\n"
        f"**Redeemed:** {redeemed} time(s)\n"
        f"**Can Redeem:** {can_redeem} time(s)\n\n"
        f"**Your Link:**\n`{ref_link}`"
    )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Share Link", url=f"https://t.me/share/url?url={ref_link}&text=Join%20this%20awesome%20bot!")],
        [InlineKeyboardButton("💎 Claim Pro", callback_data="claim_pro_ref")],
        [InlineKeyboardButton("✖ Close", callback_data="close_ref")]
    ])

    await message.reply_text(text, reply_markup=buttons, disable_web_page_preview=True)

# --- REFERRAL BUTTON CALLBACK HANDLER ---
@app.on_callback_query(filters.regex("^(claim_pro_ref|close_ref)$"))
async def ref_callback_handler(client, query):
    if query.data == "close_ref":
        await query.message.delete()
        return

    if query.data == "claim_pro_ref":
        user_id = query.from_user.id
        claimed = await redeem_referral_points(user_id)

        if claimed:
            try:
                expire_date = datetime.datetime.now() + datetime.timedelta(hours=3)
                
                # 1. Bot ni original users_db file mathi add_premium function call
                await add_premium(user_id, expire_date)
                
                # 2. Database na users collection ma seedho format update
                await users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"plan": "Premium", "plan_type": "pro", "expiry": expire_date, "expire_date": expire_date}},
                    upsert=True
                )
            except Exception:
                pass

            await query.answer("🎉 અભિનંદન! તમને ૩ કલાક માટે Pro પ્રીમિયમ પ્લાન મળી ગયો છે.", show_alert=True)
            await referral_menu(client, query.message)
        else:
            await query.answer("❌ તમારી પાસે પૂરતા રેફરલ્સ નથી! Pro મેળવવા માટે ઓછામાં ઓછા ૩ મિત્રોને જોડો.", show_alert=True)
