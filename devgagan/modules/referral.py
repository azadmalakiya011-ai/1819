import datetime
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from devgagan import app
from devgagan.core.mongo.db import db
from devgagan.core.mongo.users_db import add_premium

# --- DATABASE LOGIC ---
referral_collection = db["referrals"]

async def get_referral_data(user_id: int):
    data = await referral_collection.find_one({"user_id": user_id})
    if not data:
        data = {"user_id": user_id, "referrals": 0, "redeemed": 0}
        await referral_collection.insert_one(data)
    return data

async def add_referral(referrer_id: int, new_user_id: int):
    existing_user = await referral_collection.find_one({"user_id": new_user_id})
    if existing_user:
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

# --- START LISTENER FOR REFERRAL LINK ---
@app.on_message(filters.command("start") & filters.private, group=-1)
async def ref_start_handler(client, message: Message):
    if len(message.command) > 1 and message.command[1].startswith("ref_"):
        try:
            referrer_id = int(message.command[1].replace("ref_", ""))
            new_user_id = message.from_user.id

            if referrer_id != new_user_id:
                success = await add_referral(referrer_id, new_user_id)
                if success:
                    try:
                        await client.send_message(
                            chat_id=referrer_id,
                            text=f"🎉 **નવો રેફરલ જોડાયો!**\n\nયુઝર: {message.from_user.mention} તમારી લિંકથી જોડાયા છે."
                        )
                    except Exception:
                        pass
        except Exception:
            pass

# --- REFERRAL COMMAND MENU ---
@app.on_message(filters.command("referral") & filters.private)
async def referral_menu(client, message: Message):
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

# --- BUTTON HANDLER ---
@app.on_callback_query(filters.regex("^(claim_pro_ref|close_ref)$"))
async def ref_callback_handler(client, query: CallbackQuery):
    if query.data == "close_ref":
        await query.message.delete()
        return

    if query.data == "claim_pro_ref":
        user_id = query.from_user.id
        claimed = await redeem_referral_points(user_id)

        if claimed:
            try:
                # બરાબર ૩ કલાક માટે પ્રો પ્લાન સેટ થશે
                expire_date = datetime.datetime.now() + datetime.timedelta(hours=3)
                await add_premium(user_id, expire_date)
            except Exception:
                pass

            await query.answer("🎉 અભિનંદન! તમને ૩ કલાક માટે Pro પ્રીમિયમ મળી ગયું છે.", show_alert=True)
            await referral_menu(client, query.message)
        else:
            await query.answer("❌ તમારી પાસે પૂરતા રેફરલ્સ નથી! Pro મેળવવા માટે ઓછામાં ઓછા ૩ મિત્રોને જોડો.", show_alert=True)
  
