import asyncio
import time
import re
from pyrogram import filters
from pyrogram.errors import FloodWait
from telethon.tl.functions.messages import CreateForumTopicRequest
from devgagan import app, sex
from devgagan.modules.main import initialize_userbot
from devgagan.core.get_func import get_msg, user_chat_ids

BOT_OWNER_ID = 8326187435

user_mirror_data = {}
mirror_cancel_flags = {}
# user_id: expiry_timestamp (0 એટલે લાઈફટાઈમ)
authorized_mirror_users = {}

def parse_duration(time_str: str) -> int:
    unit = time_str[-1].lower()
    val = int(time_str[:-1])
    if unit == 's':
        return val
    elif unit == 'm':
        return val * 60
    elif unit == 'h':
        return val * 3600
    elif unit == 'd':
        return val * 86400
    elif unit == 'y':
        return val * 86400 * 365
    return 0

def is_authorized(user_id: int) -> bool:
    uid = int(user_id)
    if uid == BOT_OWNER_ID:
        return True
    if uid in authorized_mirror_users:
        expiry = authorized_mirror_users[uid]
        if expiry == 0 or time.time() < expiry:
            return True
        else:
            authorized_mirror_users.pop(uid, None)
            return False
    return False

# ----------------- એક્સેસ કંટ્રોલ કમાન્ડ્સ -----------------

@app.on_message(filters.command("addmirror") & filters.private)
async def add_mirror_access(client, message):
    if message.chat.id != BOT_OWNER_ID:
        return await message.reply_text("❌ આ કમાન્ડ માત્ર બોટ ઓનર વાપરી શકે છે.")
    
    args = message.text.strip().split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.reply_text(
            "⚠️ **વાપરવાની રીત:**\n"
            "`/addmirror <user_id> <time>`\n\n"
            "**ઉદાહરણ:**\n"
            "• ૧ કલાક: `/addmirror 123456789 1h`\n"
            "• ૧ દિવસ: `/addmirror 123456789 1d`\n"
            "• ૨ દિવસ: `/addmirror 123456789 2d`\n"
            "• ૧ વર્ષ: `/addmirror 123456789 1y`\n"
            "• કાયમી: `/addmirror 123456789`"
        )
    
    uid = int(args[1])
    duration_str = args[2] if len(args) >= 3 else None

    if duration_str:
        try:
            seconds = parse_duration(duration_str)
            if seconds <= 0:
                return await message.reply_text("❌ ખોટો સમય ફોર્મેટ! (ઉદાહરણ: 1h, 2d, 1y વાપરો)")
            expiry_time = time.time() + seconds
            authorized_mirror_users[uid] = expiry_time
            await message.reply_text(f"✅ યુઝર `{uid}` ને `{duration_str}` માટે મિરર એક્સેસ આપવામાં આવ્યો છે.")
        except Exception:
            return await message.reply_text("❌ સમય ગણતરીમાં ભૂલ થઈ. સાચો ફોર્મેટ લખો (દા.ત. 1d, 2d, 1h).")
    else:
        authorized_mirror_users[uid] = 0
        await message.reply_text(f"✅ યુઝર `{uid}` ને કાયમી (Lifetime) મિરર એક્સેસ આપવામાં આવ્યો છે.")

@app.on_message(filters.command("delmirror") & filters.private)
async def del_mirror_access(client, message):
    if message.chat.id != BOT_OWNER_ID:
        return await message.reply_text("❌ આ કમાન્ડ માત્ર બોટ ઓનર વાપરી શકે છે.")
    
    args = message.text.strip().split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.reply_text("⚠️ સાચો કમાન્ડ વાપરો: `/delmirror <user_id>`")
    
    uid = int(args[1])
    if uid in authorized_mirror_users:
        authorized_mirror_users.pop(uid, None)
        await message.reply_text(f"🚫 યુઝર `{uid}` પાસેથી મિરર એક્સેસ હટાવી દીધો છે.")
    else:
        await message.reply_text("⚠️ આ યુઝર પાસે પહેલેથી એક્સેસ નથી.")
        

# ----------------- હેલ્પર ફંક્શન્સ -----------------

async def create_topic(chat_id, title):
    if not sex or not sex.is_connected():
        raise Exception("Telethon ક્લાયન્ટ કનેક્ટ નથી.")
    entity = await sex.get_input_entity(chat_id)
    result = await sex(CreateForumTopicRequest(
        peer=entity,
        title=title[:128],
        random_id=int(time.time() * 1000)
    ))
    for update in getattr(result, "updates", []):
        msg = getattr(update, "message", None)
        if msg:
            return msg.id
    raise Exception("Topic ID બન્યો નથી.")

def parse_tg_link(link: str):
    parts = link.strip().split("/")
    idx = parts.index("c")
    chat_id = int("-100" + parts[idx + 1])
    nums = [int(x.split("?")[0]) for x in parts[idx + 2:] if x.split("?")[0].isdigit()]
    topic_id = nums[-2] if len(nums) >= 2 else 1
    msg_id = nums[-1] if nums else 1
    return chat_id, topic_id, msg_id

# ----------------- મિરર કમાન્ડ્સ -----------------

# ૧. /topicmirror - બધા ટોપિક્સ સાચા નામ સાથે સિંક કરવા
@app.on_message(filters.command("topicmirror") & filters.private)
async def topic_mirror_full(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ તમારી પાસે આ કમાન્ડ વાપરવાનો એક્સેસ નથી.")

    try:
        ask = await app.ask(user_id, "🔗 સોર્સ ગ્રુપના કોઈપણ એક મેસેજની લિંક મોકલો:")
        link = ask.text.strip()
        source_chat_id, _, _ = parse_tg_link(link)

        ask = await app.ask(user_id, "🎯 ટાર્ગેટ ગ્રુપ ID મોકલો (-100 થી શરૂ થતો):")
        target_chat_id = int(ask.text.strip())

    except Exception as e:
        return await app.send_message(user_id, f"❌ ભૂલ થઈ: `{e}`")

    status = await app.send_message(user_id, "⏳ યુઝરબોટ ચાલુ થઈ રહ્યો છે...")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ યુઝરબોટ ચાલુ નથી. પહેલા `/login` કરો.")

    try:
        await status.edit("🔍 શરૂઆતના મેસેજમાંથી સાચા નામ સાથે બધા ટોપિક્સ શોધાઈ રહ્યા છે...")
        topics = {}

 # ૧. ટેલિથોન યુઝરબોટ દ્વારા બધા પેજના ટોપિક્સ (પૂરેપૂરા ૯૯+) લાવશે
        if sex and sex.is_connected():
            try:
                from telethon.tl.functions.channels import GetForumTopicsRequest
                src_entity = await sex.get_input_entity(source_chat_id)
                offset_date = 0
                offset_id = 0
                offset_topic = 0
                
                while True:
                    forum_res = await sex(GetForumTopicsRequest(
                        channel=src_entity,
                        offset_date=offset_date,
                        offset_id=offset_id,
                        offset_topic=offset_topic,
                        limit=100
                    ))
                    raw_topics = getattr(forum_res, "topics", [])
                    if not raw_topics:
                        break
                    
                    for t in raw_topics:
                        t_id = getattr(t, "id", None)
                        t_title = getattr(t, "title", None)
                        if t_id and t_title and int(t_id) != 1:
                            topics[int(t_id)] = t_title
                    
                    # જો ૧૦૦ કરતાં ઓછા ટોપિક્સ આવે તો લૂપ બંધ થશે
                    if len(raw_topics) < 100:
                        break
                    
                    # પછીના પેજના ટોપિક્સ મેળવવા માટે ઓફસેટ સેટ કરો
                    last_t = raw_topics[-1]
                    offset_topic = getattr(last_t, "id", 0)
                    offset_date = getattr(last_t, "date", 0)
                    offset_id = getattr(last_t, "top_message", 0)
                    await asyncio.sleep(0.3)
            except Exception:
                pass

        # ૨. જો API થી પૂરા ના મળે તો હિસ્ટ્રીમાંથી ડીપ સ્કેન
        if len(topics) < 50:
            async for msg in userbot.get_chat_history(source_chat_id, limit=25000):
                if not msg or getattr(msg, "empty", False):
                    continue
                th_id = getattr(msg, "message_thread_id", None)
                created = getattr(msg, "forum_topic_created", None)
                if created and getattr(created, "title", None):
                    topics[msg.id] = created.title
                elif th_id and int(th_id) != 1 and int(th_id) not in topics:
                    topics[int(th_id)] = None

            for t_id, name in list(topics.items()):
                if not name:
                    try:
                        t_msg = await userbot.get_messages(source_chat_id, int(t_id))
                        if t_msg and getattr(t_msg, "forum_topic_created", None):
                            topics[t_id] = t_msg.forum_topic_created.title
                        else:
                            topics[t_id] = f"Topic {t_id}"
                    except Exception:
                        topics[t_id] = f"Topic {t_id}"
                        

        # ૨. જો API થી ના મળે તો જ Fallback હિસ્ટ્રી સ્કેન (કોઈ બ્રેક વગર)
        if not topics:
            async for msg in userbot.get_chat_history(source_chat_id, limit=8000):
                if not msg or getattr(msg, "empty", False):
                    continue

                th_id = getattr(msg, "message_thread_id", None)
                created = getattr(msg, "forum_topic_created", None)

                if created and getattr(created, "title", None):
                    topics[msg.id] = created.title
                elif th_id and int(th_id) != 1 and int(th_id) not in topics:
                    topics[int(th_id)] = None

            for t_id, name in list(topics.items()):
                if not name:
                    try:
                        t_msg = await userbot.get_messages(source_chat_id, int(t_id))
                        if t_msg and getattr(t_msg, "forum_topic_created", None):
                            topics[t_id] = t_msg.forum_topic_created.title
                        else:
                            topics[t_id] = f"Topic {t_id}"
                    except Exception:
                        topics[t_id] = f"Topic {t_id}"
                    

        if not topics:
            return await status.edit("❌ ગ્રુપમાંથી કોઈ ટોપિક્સ મળ્યા નહીં. ખાતરી કરો કે યુઝરબોટ એ ગ્રુપમાં છે.")

        mapped = {}
        total = len(topics)
        current = 0
        summary_lines = ["📋 **ટોપિક લિસ્ટ:**"]
        progress_msg = await app.send_message(user_id, f"🛠️ કુલ {total} ટોપિક મળ્યા! હવે નવા ગ્રુપમાં બની રહ્યા છે...")

        for t_id in sorted(topics.keys()):
            title = topics[t_id]
            current += 1
            try:
                new_id = await create_topic(target_chat_id, title)
                mapped[t_id] = new_id
                summary_lines.append(f"`{t_id}` ➔ `{title[:22]}`")
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                try:
                    new_id = await create_topic(target_chat_id, title)
                    mapped[t_id] = new_id
                    summary_lines.append(f"`{t_id}` ➔ `{title[:22]}`")
                except Exception:
                    mapped[t_id] = None
            except Exception:
                mapped[t_id] = None

            if current % 4 == 0 or current == total:
                try:
                    await progress_msg.edit("> " + "\n".join(summary_lines)[:4000])
                except Exception:
                    pass
            await asyncio.sleep(0.2)

        user_mirror_data[user_id] = {
            "source_chat_id": source_chat_id,
            "target_chat_id": target_chat_id,
            "mapped_topics": mapped
        }

        created_count = sum(1 for v in mapped.values() if v)
        await status.edit(
            f"🎉 **બધા ટોપિક્સ સિંક થઈ ગયા!**\n"
            f"બનેલા ટોપિક્સ: `{created_count}` / `{total}`\n\n"
            "👉 ચોક્કસ ટોપિક મિરર કરવા માટે: `/topiclink`\n"
            "👉 બાકી રહેલી ફાઈલો સિંક કરવા માટે: `/sync_mirror`"
        )
    finally:
        try:
            await userbot.stop()
        except Exception:
            pass

# ૨. /topiclink - Game te Group ni Link to Link Transfer
@app.on_message(filters.command("topiclink") & filters.private)
async def topic_link_direct(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ Tamari pase aa command vaparvano access nathi.")

    try:
        ask = await app.ask(user_id, "🔗 Source topic na video/message ni link moklo:")
        s_link = ask.text.strip()
        s_chat_id, s_topic_id, s_msg_id = parse_tg_link(s_link)

        ask = await app.ask(user_id, "🔗 Target group na topic ni link moklo:")
        t_link = ask.text.strip()
        t_chat_id, t_topic_id, _ = parse_tg_link(t_link)
    except Exception as e:
        return await app.send_message(user_id, f"❌ Link vanchvama bhul thai: `{e}`")

    mirror_cancel_flags[user_id] = False
    user_chat_ids[user_id] = f"{t_chat_id}/{t_topic_id}"

    status = await app.send_message(
        user_id, 
        f"🚀 Video `{s_msg_id}` thi sharu kari ne target topic `{t_topic_id}` ma transfer thai rahya chhe...\n(Rokva mate `/cancel_mirror` moklo)"
    )
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ Userbot chalu nathi. Pahela `/login` karo.")

    success = 0
    try:
        target_msgs = []
        async for msg in userbot.get_chat_history(s_chat_id, limit=2000):
            if not msg or getattr(msg, "empty", False) or getattr(msg, "service", False):
                continue
            
            th_id = getattr(msg, "message_thread_id", None) or s_topic_id
            if int(th_id) == int(s_topic_id) and msg.media:
                if msg.id >= s_msg_id:
                    target_msgs.append(msg)

        target_msgs.reverse()

        for msg in target_msgs:
            if mirror_cancel_flags.get(user_id, False):
                break

            temp = await app.send_message(user_id, f"🔄 Processing video `{msg.id}`...")
            fake_link = f'https://t.me/c/{str(s_chat_id).replace("-100", "")}/{msg.id}'
            
            try:
                await get_msg(userbot, user_id, temp.id, fake_link, 0, message)
                success += 1
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except Exception:
                pass
            finally:
                try:
                    await temp.delete()
                except Exception:
                    pass
            await asyncio.sleep(2)

        await status.edit(f"🎉 **Transfer puru thayu!**\n✅ Safal files: `{success}`")
    finally:
        mirror_cancel_flags.pop(user_id, None)
        user_chat_ids.pop(user_id, None)
        try:
            await userbot.stop()
        except Exception:
            pass
            

# 3. /scan_mirror - Perfect Scan ane Comparison
@app.on_message(filters.command("scan_mirror") & filters.private)
async def scan_mirror_compare(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ Tamari pase aa command vaparvano access nathi.")

    try:
        ask = await app.ask(user_id, "🔗 Source topic ni link moklo:")
        s_link = ask.text.strip()
        s_chat_id, s_topic_id, _ = parse_tg_link(s_link)

        ask = await app.ask(user_id, "🔗 Target topic ni link moklo:")
        t_link = ask.text.strip()
        t_chat_id, t_topic_id, _ = parse_tg_link(t_link)
    except Exception as e:
        return await app.send_message(user_id, f"❌ Link vanchvama bhul thai: `{e}`")

    status = await app.send_message(user_id, "🔍 Banne topic scan thai rahya chhe...")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ Userbot chalu nathi. Pahela `/login` karo.")

    try:
        # Target topic scan karvo
        target_files = set()
        t_count = 0
        async for t_msg in userbot.get_chat_history(t_chat_id, limit=2000):
            if not t_msg or getattr(t_msg, "empty", False) or getattr(t_msg, "service", False):
                continue
            
            th_id = getattr(t_msg, "message_thread_id", None)
            if (th_id and int(th_id) == int(t_topic_id)) or (not th_id and int(t_topic_id) == 1):
                if t_msg.media:
                    t_count += 1
                    media_obj = getattr(t_msg, t_msg.media.value, None)
                    if media_obj:
                        f_id = getattr(media_obj, "file_unique_id", None) or getattr(media_obj, "file_size", None)
                        if f_id:
                            target_files.add(str(f_id))

        # Source topic scan karvo
        s_count = 0
        missing_count = 0
        async for s_msg in userbot.get_chat_history(s_chat_id, limit=2000):
            if not s_msg or getattr(s_msg, "empty", False) or getattr(s_msg, "service", False):
                continue

            th_id = getattr(s_msg, "message_thread_id", None)
            if (th_id and int(th_id) == int(s_topic_id)) or (not th_id and int(s_topic_id) == 1):
                if s_msg.media:
                    s_count += 1
                    media_obj = getattr(s_msg, s_msg.media.value, None)
                    if media_obj:
                        f_id = getattr(media_obj, "file_unique_id", None) or getattr(media_obj, "file_size", None)
                        if str(f_id) not in target_files:
                            missing_count += 1

        res_text = (
            "📊 **સ્કેન અને સરખામણીનું પરિણામ:**\n\n"
            f"📁 જૂના ટોપિકમાં મીડિયા: `{s_count}`\n"
            f"📁 નવા ટોપિકમાં મીડિયા: `{t_count}`\n"
            f"⚠️ બાકી રહેલી ફાઈલો: `{missing_count}`\n\n"
            "બાકી રહેલી ફાઈલો મોકલવા માટે `/sync_mirror` ચલાવો."
        )
        await status.edit(res_text)

    except Exception as e:
        await status.edit(f"❌ Scan karti vakhate bhul thai: `{e}`")
    finally:
        try:
            await userbot.stop()
        except Exception:
            pass
            

# ૪. /sync_mirror - બાકી રહેલી ફાઇલો સિંક કરવી
@app.on_message(filters.command("sync_mirror") & filters.private)
async def sync_mirror_missing(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ તમારી પાસે આ કમાન્ડ વાપરવાનો એક્સેસ નથી.")

    try:
        ask = await app.ask(user_id, "🔗 સોર્સ ટોપિકની લિંક મોકલો:")
        s_link = ask.text.strip()
        s_chat_id, s_topic_id, _ = parse_tg_link(s_link)

        ask = await app.ask(user_id, "🔗 ટાર્ગેટ ટોપિકની લિંક મોકલો:")
        t_link = ask.text.strip()
        t_chat_id, t_topic_id, _ = parse_tg_link(t_link)
    except Exception as e:
        return await app.send_message(user_id, f"❌ ભૂલ થઈ: `{e}`")

    mirror_cancel_flags[user_id] = False
    user_chat_ids[user_id] = f"{t_chat_id}/{t_topic_id}"
    status = await app.send_message(user_id, "🔄 બાકી રહેલા વિડિયો સ્કેન અને સિંક થઈ રહ્યા છે...")

    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ યુઝરબોટ ચાલુ નથી. પહેલા `/login` કરો.")

    try:
        target_file_ids = set()
        async for t_msg in userbot.get_chat_history(t_chat_id, limit=500):
            th_id = getattr(t_msg, "message_thread_id", None) or t_topic_id
            if int(th_id) == int(t_topic_id) and t_msg.media:
                media_obj = getattr(t_msg, t_msg.media.value, None)
                if media_obj:
                    f_id = getattr(media_obj, "file_unique_id", None) or getattr(media_obj, "file_size", None)
                    if f_id:
                        target_file_ids.add(str(f_id))

        missing_msgs = []
        async for s_msg in userbot.get_chat_history(s_chat_id, limit=500):
            th_id = getattr(s_msg, "message_thread_id", None) or s_topic_id
            if int(th_id) == int(s_topic_id) and s_msg.media:
                media_obj = getattr(s_msg, s_msg.media.value, None)
                if media_obj:
                    f_id = getattr(media_obj, "file_unique_id", None) or getattr(media_obj, "file_size", None)
                    if str(f_id) not in target_file_ids:
                        missing_msgs.append(s_msg)

        missing_msgs.reverse()

        if not missing_msgs:
            return await status.edit("✅ બધી ફાઈલો પહેલેથી સિંક છે. કોઈ ફાઈલ બાકી નથી.")

        synced = 0
        for s_msg in missing_msgs:
            if mirror_cancel_flags.get(user_id, False):
                break

            temp = await app.send_message(user_id, f"🔄 પ્રોસેસિંગ બાકી વિડિયો `{s_msg.id}`...")
            uploaded = False

            try:
                await userbot.copy_message(
                    chat_id=t_chat_id,
                    from_chat_id=s_chat_id,
                    message_id=s_msg.id,
                    message_thread_id=t_topic_id
                )
                uploaded = True
                synced += 1
            except Exception:
                pass

            if not uploaded:
                fake_link = f'https://t.me/c/{str(s_chat_id).replace("-100", "")}/{s_msg.id}'
                try:
                    await get_msg(userbot, user_id, temp.id, fake_link, 0, message)
                    synced += 1
                except FloodWait as e:
                    await asyncio.sleep(e.value + 1)
                except Exception:
                    pass

            try:
                await temp.delete()
            except Exception:
                pass
            await asyncio.sleep(2)

        await status.edit(f"🎉 **સિંકિંગ પૂરું થયું!**\n✅ બાકી ફાઈલો ટ્રાન્સફર થઈ: `{synced}`")
    finally:
        mirror_cancel_flags.pop(user_id, None)
        user_chat_ids.pop(user_id, None)
        try:
            await userbot.stop()
        except Exception:
            pass
            

# ૫. /cancel_mirror - ચાલુ મિરરિંગ રોકવા માટે
@app.on_message(filters.command(["cancel_mirror", "stopmirror"]) & filters.private)
async def cancel_mirror_handler(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ તમારી પાસે આ કમાન્ડ વાપરવાનો એક્સેસ નથી.")

    if user_id in mirror_cancel_flags:
        mirror_cancel_flags[user_id] = True
        await message.reply_text("🛑 **મિરરિંગ રોકવાની વિનંતી સ્વીકારી લીધી છે!** હાલની ફાઈલ પૂરી થતાં જ બંધ થઈ જશે.")
    else:
        await message.reply_text("⚠️ હાલમાં કોઈ મિરરિંગ પ્રોસેસ ચાલુ નથી.")



# ૬. /mirror_all - જ્યાંથી બાકી હોય ત્યાંથી જ ઓટો-રીઝ્યૂમ અને કમ્પ્લીટ મેસેજ સાથે
@app.on_message(filters.command("mirror_all") & filters.private)
async def mirror_all_topics_handler(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ તમારી પાસે આ કમાન્ડ વાપરવાનો એક્સેસ નથી.")

    data = user_mirror_data.get(user_id)
    if not data or "mapped_topics" not in data or not data["mapped_topics"]:
        return await message.reply_text("❌ પહેલા `/topicmirror` રન કરો જેથી ટોપિક્સ મેપ થઈ જાય.")

    s_chat_id = data["source_chat_id"]
    t_chat_id = data["target_chat_id"]
    mapped = {int(k): int(v) for k, v in data["mapped_topics"].items() if v}

    mirror_cancel_flags[user_id] = False
    status = await app.send_message(user_id, f"🚀 **કુલ {len(mapped)} ટોપિક્સનું સ્માર્ટ મિરરિંગ શરૂ થઈ રહ્યું છે...**\n(વચ્ચે રોકવા માટે `/cancel_mirror` મોકલો)")

    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ યુઝરબોટ ચાલુ નથી. પહેલા `/login` કરો.")

    total_synced_all = 0
    try:
        topic_items = sorted(mapped.items())
        for idx, (s_topic, t_topic) in enumerate(topic_items, 1):
            if mirror_cancel_flags.get(user_id, False):
                await app.send_message(user_id, "🛑 મિરરિંગ રોકી દેવામાં આવ્યું છે.")
                break

            user_chat_ids[user_id] = f"{t_chat_id}/{t_topic}"

            # ૧. ટાર્ગેટ ટોપિકમાં છેલ્લે ક્યાં સુધી ફાઇલ આવી તે ચેક કરો (Resume Logic)
            last_synced_src_id = 0
            is_already_done = False
            async for t_msg in userbot.get_chat_history(t_chat_id, limit=30):
                th_id = getattr(t_msg, "message_thread_id", None) or t_topic
                if int(th_id) == int(t_topic):
                    if t_msg.text and "તમામ ફાઇલો સફળતાપૂર્વક અપલોડ" in t_msg.text:
                        is_already_done = True
                        break
                    txt = t_msg.caption or t_msg.text or ""
                    m = re.search(rf"/c/{str(s_chat_id).replace('-100', '')}/(\d+)", txt)
                    if m:
                        last_synced_src_id = max(last_synced_src_id, int(m.group(1)))

            # જો ટોપિક પહેલેથી જ પૂરો થઈ ગયો હોય તો સ્કીપ કરો
            if is_already_done:
                continue

            await status.edit(f"⏳ **પ્રગતિ:** ટોપિક `{idx}/{len(mapped)}` (ID: `{s_topic}`) ના બાકી વિડિયો ટ્રાન્સફર થઈ રહ્યા છે...")

            topic_video_count = 0
            src_messages = []
            async for msg in userbot.get_chat_history(s_chat_id, limit=1000):
                th_id = getattr(msg, "message_thread_id", None) or s_topic
                if int(th_id) == int(s_topic) and msg.media:
                    if msg.id > last_synced_src_id:
                        src_messages.append(msg)

            src_messages.reverse()

            for msg in src_messages:
                if mirror_cancel_flags.get(user_id, False):
                    break

                temp = await app.send_message(user_id, f"🔄 પ્રોસેસિંગ ટોપિક `{s_topic}` - ફાઇલ `{msg.id}`...")
                fake_link = f'https://t.me/c/{str(s_chat_id).replace("-100", "")}/{msg.id}'
                try:
                    await get_msg(userbot, user_id, temp.id, fake_link, 0, message)
                    total_synced_all += 1
                    topic_video_count += 1
                except FloodWait as e:
                    await asyncio.sleep(e.value + 1)
                except Exception:
                    pass
                finally:
                    try:
                        await temp.delete()
                    except Exception:
                        pass
                await asyncio.sleep(2)

            # ટોપિક પૂરો થાય એટલે કમ્પ્લીટ મેસેજ મોકલવો
            if not mirror_cancel_flags.get(user_id, False):
                try:
                    await app.send_message(
                        chat_id=t_chat_id,
                        text=f"✅ **ટોપિક પૂર્ણ!**\nઆ ટોપિકની તમામ ફાઇલો સફળતાપૂર્વક અપલોડ થઈ ગઈ છે.",
                        message_thread_id=t_topic
                    )
                except Exception:
                    pass

            await asyncio.sleep(1)

        await status.edit(f"🎉 **બધા ટોપિક્સનું મિરરિંગ પૂરું થયું!**\n✅ કુલ નવી ટ્રાન્સફર થયેલી ફાઇલો: `{total_synced_all}`")
    finally:
        mirror_cancel_flags.pop(user_id, None)
        user_chat_ids.pop(user_id, None)
        try:
            await userbot.stop()
        except Exception:
            pass





# ૫. /sync_group - સોર્સ લિંક અને ટાર્ગેટ Chat ID સાથે આખું ગ્રૂપ સિંક કરવું
@app.on_message(filters.command("sync_group") & filters.private)
async def sync_entire_group(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ તમારી પાસે આ કમાન્ડ વાપરવાનો એક્સેસ નથી.")

    try:
        # ૧. સોર્સ ગ્રૂપની લિંક મેળવવી
        ask = await app.ask(user_id, "🔗 **સોર્સ ગ્રૂપની લિંક (કોઈપણ મેસેજ કે ટોપિકની લિંક) મોકલો:**")
        s_link = ask.text.strip()
        s_chat_id, _, _ = parse_tg_link(s_link)

        # ૨. ટાર્ગેટ ગ્રૂપની Chat ID અથવા લિંક મેળવવી
        ask = await app.ask(user_id, "🎯 **તમારા ટાર્ગેટ ગ્રૂપની Chat ID (દા.ત. -1004319237048) અથવા લિંક મોકલો:**")
        t_input = ask.text.strip()

        if t_input.startswith("-100") or t_input.lstrip("-").isdigit():
            t_chat_id = int(t_input)
        else:
            t_chat_id, _, _ = parse_tg_link(t_input)

    except Exception as e:
        return await app.send_message(user_id, f"❌ ઇનપુટ વાંચવામાં ભૂલ થઈ: `{e}`")

    start_time = time.time()
    mirror_cancel_flags[user_id] = False
    status = await app.send_message(user_id, "🔍 **બંને ગ્રૂપના બધા ટોપિક્સ અને ફાઈલો સ્કેન થઈ રહ્યા છે...**")

    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ યુઝરબોટ ચાલુ નથી. પહેલા `/login` કરો.")

    try:
        # ૧. ટાર્ગેટ ગ્રૂપના ટોપિક્સ અને હાજર ફાઈલો મેપ કરવી
        target_topics = {}  # {topic_name: {"id": thread_id, "files": set()}}
        async for t_msg in userbot.get_chat_history(t_chat_id, limit=3000):
            th_id = getattr(t_msg, "message_thread_id", None) or getattr(t_msg, "reply_to_top_message_id", 1)
            
            # ટોપિક નામ મેળવવું
            if getattr(t_msg, "forum_topic_created", None):
                t_name = t_msg.forum_topic_created.name.strip().lower()
                if t_name not in target_topics:
                    target_topics[t_name] = {"id": t_msg.id, "files": set()}

            # ફાઈલો નોંધવી
            key = get_media_info(t_msg)
            if key:
                for t_name, data in target_topics.items():
                    if data["id"] == th_id:
                        data["files"].add(key)

        # ૨. સોર્સ ગ્રૂપના ટોપિક્સ અને મીડિયા મેસેજ કલેક્ટ કરવા
        source_topics = {}  # {topic_name: {"id": thread_id, "msgs": []}}
        source_id_to_name = {}
        async for s_msg in userbot.get_chat_history(s_chat_id, limit=3000):
            if getattr(s_msg, "forum_topic_created", None):
                s_name = s_msg.forum_topic_created.name.strip().lower()
                source_topics[s_name] = {"id": s_msg.id, "msgs": []}
                source_id_to_name[s_msg.id] = s_name

            th_id = getattr(s_msg, "message_thread_id", None) or getattr(s_msg, "reply_to_top_message_id", 1)
            if th_id in source_id_to_name:
                s_name = source_id_to_name[th_id]
                key = get_media_info(s_msg)
                if key:
                    source_topics[s_name]["msgs"].append((key, s_msg))

        total_synced_files = 0
        total_already_files = 0

        # ૩. દરેક મેચ થતા ટોપિકમાં બાકી રહેલી ફાઈલો ટ્રાન્સફર કરવી
        for t_name, s_data in source_topics.items():
            if mirror_cancel_flags.get(user_id, False):
                break

            if t_name in target_topics:
                t_topic_id = target_topics[t_name]["id"]
                t_files = target_topics[t_name]["files"]
                
                # માત્ર ખૂટતી ફાઈલો ફિલ્ટર કરવી
                pending_msgs = [msg for key, msg in s_data["msgs"] if key not in t_files]
                pending_msgs.reverse()

                topic_new_count = 0
                total_already_files += len(t_files)

                if pending_msgs:
                    await status.edit(f"📂 **ટોપિક સિંક થઈ રહ્યો છે:** `{t_name}`\n⏳ બાકી ફાઈલો: `{len(pending_msgs)}`")

                    for s_msg in pending_msgs:
                        if mirror_cancel_flags.get(user_id, False):
                            break

                        uploaded = False
                        user_chat_ids[user_id] = f"{t_chat_id}/{t_topic_id}"

                        # ડાયરેક્ટ કોપી
                        try:
                            await userbot.copy_message(
                                chat_id=t_chat_id,
                                from_chat_id=s_chat_id,
                                message_id=s_msg.id,
                                message_thread_id=t_topic_id
                            )
                            uploaded = True
                            topic_new_count += 1
                        except Exception:
                            pass

                        # કોપી ન થાય તો ડાઉનલોડ/અપલોડ
                        if not uploaded:
                            temp = await app.send_message(user_id, f"🔄 પ્રોસેસિંગ `{s_msg.id}`...")
                            fake_link = f'https://t.me/c/{str(s_chat_id).replace("-100", "")}/{s_msg.id}'
                            try:
                                await get_msg(userbot, user_id, temp.id, fake_link, 0, message)
                                topic_new_count += 1
                            except FloodWait as e:
                                await asyncio.sleep(e.value + 1)
                            except Exception:
                                pass
                            try:
                                await temp.delete()
                            except Exception:
                                pass

                        await asyncio.sleep(2)

                    total_synced_files += topic_new_count

                                    # સમયની ગણતરી
        elapsed = time.time() - start_time
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        time_taken_str = f"{mins}m, {secs}s"

        general_complete_msg = f"✅ Complete Ho Gaya Boss 😎\n\n📁 New Files Downloaded & Synced: {total_synced_files} files\n⏩ Already Up-to-date: {total_already_files} files\n⏱ Time Taken: {time_taken_str}"
    

        # General Chat માં મોકલવું
        try:
            await app.send_message(chat_id=t_chat_id, text=general_complete_msg)
        except Exception:
            try:
                await userbot.send_message(chat_id=t_chat_id, text=general_complete_msg)
            except Exception:
                pass

        await status.edit(f"🎉 **આખા ગ્રૂપનું સિંકિંગ સફળતાપૂર્વક પૂરું થયું!**\n\n{general_complete_msg}")

    except Exception as e:
        await status.edit(f"❌ એરર આવી: `{e}`")
    finally:
        mirror_cancel_flags.pop(user_id, None)
        user_chat_ids.pop(user_id, None)
        try:
            await userbot.stop()
        except Exception:
            pass
            
