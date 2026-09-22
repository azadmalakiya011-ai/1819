import datetime, asyncio
from pyrogram import filters, StopPropagation
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message, BotCommand
from devgagan import app
from config import OWNER_ID
from devgagan.core.func import subscribe, chk_user
from devgagan.core.mongo.db import db
from devgagan.core.mongo.plans_db import premium_users

referral_collection = db["referrals"]
users_collection = db["users"]
plans_collection = db["plans"]
tokens_collection = db["tokens"]

async def get_referral_data(user_id: int):
    data = await referral_collection.find_one({"user_id": user_id})
    if not data:
        data = {"user_id": user_id, "referrals": 0, "redeemed": 0}
        await referral_collection.insert_one(data)
    return data

async def add_referral(referrer_id: int, new_user_id: int):
    if await premium_users.find_one({"user_id": new_user_id}) or await users_collection.find_one({"user_id": new_user_id}) or await referral_collection.find_one({"user_id": new_user_id}):
        return False
    await referral_collection.insert_one({"user_id": new_user_id, "referrals": 0, "redeemed": 0})
    await referral_collection.update_one({"user_id": referrer_id}, {"$inc": {"referrals": 1}}, upsert=True)
    return True

async def redeem_referral_points(user_id: int):
    data = await get_referral_data(user_id)
    if data.get("referrals", 0) - (data.get("redeemed", 0) * 3) >= 3:
        await referral_collection.update_one({"user_id": user_id}, {"$inc": {"redeemed": 1}})
        return True
    return False

@app.on_message(filters.command("start") & filters.private, group=-1)
async def ref_start_handler(client, message: Message):
    if len(message.command) > 1 and str(message.command[1]).startswith("ref_"):
        try:
            referrer_id = int(message.command[1].replace("ref_", ""))
        except ValueError:
            return
        if referrer_id == message.from_user.id:
            await message.reply_text("❌ તમે પોતાની લિંક વાપરી શકતા નથી!")
            return
        if await add_referral(referrer_id, message.from_user.id):
            try:
                await client.send_message(referrer_id, f"🎉 **નવો રેફરલ જોડાયો:** {message.from_user.mention}")
            except Exception:
                pass
            await message.reply_text(f"👋 **નમસ્તે {message.from_user.first_name}!**\n\n🎉 તમે રેફરલ લિંકથી સફળતાપૂર્વક જોડાયા છો.\n👉 બોટ વાપરવા /token મેળવો અથવા /referral થી Pro મેળવો!")
        else:
            await message.reply_text(f"👋 **નમસ્તે {message.from_user.first_name}!**\n\n⚠️ તમે પહેલેથી બોટના સભ્ય છો, જેથી રેફરલ ગણાયો નથી.\n👉 બોટ વાપરવા /token મેળવો અથવા મિત્રોને /referral થી જોડો!")
        return

@app.on_message(filters.command("set"))
async def set(_, message):
    if message.from_user.id not in OWNER_ID:
        return await message.reply("You are not authorized.")
    await app.set_bot_commands([
        BotCommand("start", "🚀 Start"), BotCommand("batch", "🫠 Extract bulk"), BotCommand("login", "🔑 Login"),
        BotCommand("logout", "🚪 Logout"), BotCommand("token", "🎲 Free access"), BotCommand("referral", "🎁 Invite friends"),
        BotCommand("myplan", "⌛ Plan details"), BotCommand("plans", "🗓️ Premium plans"), BotCommand("help", "❓ Help"),
        BotCommand("cancel", "🚫 Cancel process"), BotCommand("settings", "⚙️ Settings")
    ])
    await message.reply("✅ Commands configured successfully!")

@app.on_message(filters.command("help"))
async def help(client, message):
    if await subscribe(client, message) == 1:
        return
    await message.reply("📝 **Bot Commands:**\n/batch - Bulk download\n/login - Login account\n/token - Get session\n/referral - Refer friends\n/myplan - Check plan")

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

@app.on_message(filters.command("referral") & filters.private)
async def referral_menu(client, message):
    user_id = message.from_user.id
    bot_user = (await client.get_me()).username
    data = await get_referral_data(user_id)
    t_refs, red = data.get("referrals", 0), data.get("redeemed", 0)
    can_red = (t_refs - (red * 3)) // 3
    ref_link = f"https://t.me/{bot_user}?start=ref_{user_id}"
    
    text = f"👑 **{message.from_user.first_name}**\n🎁 **Referral Program**\n\n3 Referrals = 3 Hours Pro\n\n**Your Referrals:** {t_refs}\n**Redeemed:** {red}\n**Can Redeem:** {can_red}\n\n`{ref_link}`"
    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Share Link", url=f"https://t.me/share/url?url={ref_link}&text=Join%20this%20bot!")],
        [InlineKeyboardButton("💎 Claim Pro", callback_data="claim_pro_ref")],
        [InlineKeyboardButton("✖ Close", callback_data="close_ref")]
    ])
    await message.reply_text(text, reply_markup=btns, disable_web_page_preview=True)

@app.on_callback_query(filters.regex("^(claim_pro_ref|close_ref)$"))
async def ref_callback_handler(client, query):
    if query.data == "close_ref":
        return await query.message.delete()
    if query.data == "claim_pro_ref":
        user_id = query.from_user.id
        if await redeem_referral_points(user_id):
            exp = datetime.datetime.now() + datetime.timedelta(hours=3)
            await premium_users.update_one({"user_id": user_id}, {"$set": {"user_id": user_id, "expiry_time": exp, "plan": "Pro 3 Hours"}}, upsert=True)
            u_data = {"user_id": user_id, "plan": "Premium", "plan_type": "pro", "expire_date": exp, "expiry_date": exp, "expiry": exp}
            await users_collection.update_one({"user_id": user_id}, {"$set": u_data}, upsert=True)
            await plans_collection.update_one({"user_id": user_id}, {"$set": u_data}, upsert=True)
            await tokens_collection.update_one({"user_id": user_id}, {"$set": {"user_id": user_id, "param": "REFERRAL_PRO", "expires_at": exp}}, upsert=True)
            await query.answer("🎉 Claim Successful!", show_alert=True)
            await query.message.reply_text("🎉 **અભિનંદન!** તમને ૩ કલાક માટે Pro Plan મળી ગયો છે. હવે /myplan ચેક કરો.")
            await referral_menu(client, query.message)
        else:
            await query.answer("❌ પૂરતા રેફરલ્સ નથી!", show_alert=True)
            await query.message.reply_text("❌ **તમારી પાસે પૂરતા રેફરલ્સ નથી!**\nદર ૩ રેફરલે ૧ વાર Pro મળશે.")
      
