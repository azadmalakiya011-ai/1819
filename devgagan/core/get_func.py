# ---------------------------------------------------
# File Name: get_func.py
# Description: A Pyrogram bot for downloading files from Telegram channels or groups 
#              and uploading them back to Telegram.
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# Telegram: https://t.me/team_spy_pro
# YouTube: https://youtube.com/@dev_gagan
# Created: 2025-01-11
# Last Modified: 2025-02-01
# Version: 2.0.5
# License: MIT License
# Improved logic handles
# ---------------------------------------------------

import asyncio
import time
import gc
import os
import re
from typing import Callable
from devgagan import app
import aiofiles
from devgagan import sex as gf
from telethon.tl.types import DocumentAttributeVideo, Message
from telethon.sessions import StringSession
import pymongo
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid
from pyrogram.enums import MessageMediaType, ParseMode
from devgagan.core.func import *
from pyrogram.errors import RPCError
from pyrogram.types import Message
from config import MONGO_DB as MONGODB_CONNECTION_STRING, LOG_GROUP, OWNER_ID, STRING, API_ID, API_HASH
from devgagan.core.mongo import db as odb
from telethon import TelegramClient, events, Button
from devgagantools import fast_upload
from datetime import datetime
import unicodedata
import random

# Clean filename helper

def clean_filename(text):
    if not text:
        return "file"

    # Normalize to separate combined accents
    text = unicodedata.normalize("NFKC", text)

    # Remove emojis and unwanted symbols (but keep letters from all scripts)
    text = ''.join(
        char for char in text
        if not unicodedata.category(char).startswith('S')  # Symbols (includes emojis)
        and not unicodedata.category(char).startswith('C')  # Other (control chars, etc.)
        and not unicodedata.category(char).startswith('P')  # Punctuation
        or char in ['.', '-', '_']  # keep basic filename-safe symbols
    )

    # Normalize spaces, dashes, underscores
    text = re.sub(r'[_\s\-]+', ' ', text)

    # Final strip
    return text.strip()


def thumbnail(sender):
    path = os.path.join(THUMBNAIL_DIR, f"{sender}.jpg")
    return path if os.path.exists(path) else None


THUMBNAIL_DIR = "./thumbnails"
os.makedirs(THUMBNAIL_DIR, exist_ok=True)

# MongoDB database name and collection name
DB_NAME = "smart_users"
COLLECTION_NAME = "super_user"

VIDEO_EXTENSIONS = ['mp4', 'mov', 'avi', 'mkv', 'flv', 'wmv', 'webm', 'mpg', 'mpeg', '3gp', 'ts', 'm4v', 'f4v', 'vob']
DOCUMENT_EXTENSIONS = ['pdf', 'docs']

mongo_app = pymongo.MongoClient(MONGODB_CONNECTION_STRING)
db = mongo_app[DB_NAME]
collection = db[COLLECTION_NAME]

if STRING:
    from devgagan import pro
    print("App imported")
else:
    pro = None
    print("STRING is not available. 'app' is set to None.")
    
async def fetch_upload_method(user_id):
    """Fetch the user's preferred upload method."""
    user_data = collection.find_one({"user_id": user_id})
    return user_data.get("upload_method", "Pyrogram") if user_data else "Pyrogram"


def format_caption_to_html(caption: str) -> str:
    if not caption:
        return None

    caption = re.sub(r"^> (.*)", r"<blockquote>\1</blockquote>", caption, flags=re.MULTILINE)
    caption = re.sub(r"```(.*?)```", r"<pre>\1</pre>", caption, flags=re.DOTALL)
    caption = re.sub(r"`(.*?)`", r"<code>\1</code>", caption)
    caption = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", caption)
    caption = re.sub(r"\*(.*?)\*", r"<b>\1</b>", caption)
    caption = re.sub(r"__(.*?)__", r"<i>\1</i>", caption)
    caption = re.sub(r"_(.*?)_", r"<i>\1</i>", caption)
    caption = re.sub(r"~~(.*?)~~", r"<s>\1</s>", caption)
    caption = re.sub(r"\|\|(.*?)\|\|", r"<details>\1</details>", caption)
    caption = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2">\1</a>', caption)
    
    return caption.strip()


# Unified log_upload
async def log_upload(user_id, file_type, file_msg, upload_method, duration=None, file_name=None):
    try:
        user = await app.get_users(user_id)
        bot = await app.get_me()

        user_mention = user.mention if user else "User"
        bot_name = f"{bot.first_name} (@{bot.username})" if bot else "Unknown Bot"
        display_text = file_msg.caption or file_name or "No caption/filename"
        clean_text = (display_text[:1000] + '...') if len(display_text) > 1000 else display_text

        text = (
            f"{clean_text}\n\n"
            f"📁 **log info:**\n"
            f"👤 **User:** {user_mention}\n"
            f"🆔 **User ID:** `{user_id}`\n"
        )

        text += f"🤖 **Saved by:** {bot_name}"

        if LOG_GROUP and file_msg:
            await file_msg.forward(LOG_GROUP)

    except Exception as e:
        await app.send_message(LOG_GROUP, f"❌ Log Error: `{e}`")


# Upload handler
async def upload_media(sender, target_chat_id, file, caption, edit, topic_id):
    try:
        upload_method = await fetch_upload_method(sender)
        
        # Safe default values to prevent cv2 memory spike
        width, height, duration = 1280, 720, 0
        thumb_path = thumbnail(sender) or await screenshot(file, duration, sender)

        ext = file.split('.')[-1].lower()
        raw_name = os.path.basename(file)
        clean_name = clean_filename(os.path.splitext(raw_name)[0])
        file_name = f"{clean_name}.{ext}"

        video_formats = {'mp4', 'mkv', 'avi', 'mov'}
        image_formats = {'jpg', 'png', 'jpeg'}

        # ✅ Generate cleaned caption for user post
        caption = format_caption(caption, sender, custom_caption=None)

        # ✅ Generate log caption separately
        user = await app.get_users(sender)
        bot = await app.get_me()
        user_mention = user.mention if user else "User"
        bot_name = f"{bot.first_name} (@{bot.username})" if bot else "Bot"

        display_text = caption or file_name or "No caption/filename"
        clean_text = (display_text[:1000] + '...') if len(display_text) > 1000 else display_text

        log_caption = (            
            f"📁 **log info:**\n"
            f"👤 **User:** {user_mention}\n"
            f"🆔 **User ID:** `{sender}`\n"
            f"🤖 **Saved by:** {bot_name}"
        )

        gc.collect()

        # ────── Pyrogram Upload ──────
        if upload_method == "Pyrogram":
            if ext in video_formats:
                # Send to user
                dm = await app.send_video(
                    chat_id=target_chat_id,
                    video=file,
                    caption=caption,
                    supports_streaming=True,
                    thumb=thumb_path,
                    reply_to_message_id=topic_id,
                    parse_mode=ParseMode.MARKDOWN,
                    progress=progress_bar,
                    progress_args=("╔══━⚡️Uploading...⚡️━══╗\n", edit, time.time())
                )

                if LOG_GROUP and dm:
                    await dm.forward(LOG_GROUP)

            elif ext in image_formats:
                dm = await app.send_photo(
                    chat_id=target_chat_id,
                    photo=file,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    progress=progress_bar,
                    reply_to_message_id=topic_id,
                    progress_args=("╔══━⚡️Uploading...⚡️━══╗\n", edit, time.time())
                )

                if LOG_GROUP and dm:
                    await dm.forward(LOG_GROUP)

            else:
                dm = await app.send_document(
                    chat_id=target_chat_id,
                    document=file,
                    caption=caption,
                    thumb=thumb_path,
                    reply_to_message_id=topic_id,
                    parse_mode=ParseMode.MARKDOWN,
                    progress=progress_bar,
                    progress_args=("╔══━⚡️Uploading...⚡️━══╗\n", edit, time.time())
                )
                if LOG_GROUP and dm:
                    await dm.forward(LOG_GROUP)

        # ────── Telethon Upload ──────
        elif upload_method == "Telethon":
            await edit.delete()
            progress_message = await gf.send_message(sender, "**__Uploading...__**")
            caption_html = await format_caption_to_html(caption)

            uploaded = await fast_upload(
                gf, file,
                reply=progress_message,
                name=file_name,
                progress_bar_function=lambda done, total: progress_callback(done, total, sender)
            )
            await progress_message.delete()

            attributes = [
                DocumentAttributeVideo(duration=duration, w=width, h=height, supports_streaming=True)
            ] if ext in video_formats else []

            bot = await app.get_me()
            bot_name = f"{bot.first_name} (@{bot.username})" if bot else "Bot"

            log_caption = (
                f"📁 **File Name:** {file_name}\n\n"
                f"📤 **Upload Info**\n"
                f"👤 **User:** [{sender}](tg://user?id={sender})\n"
                f"🆔 **User ID:** `{sender}`\n"
                f"🗂️ **Type:** `{ext.upper()}`\n"
            )

            await gf.send_file(
                target_chat_id,
                uploaded,
                caption=caption_html,
                attributes=attributes,
                reply_to=topic_id,
                thumb=thumb_path
            )

            await gf.send_file(
                LOG_GROUP,
                uploaded,
                caption=log_caption,
                attributes=attributes,
                thumb=thumb_path
            )

    except Exception as e:
        await app.send_message(LOG_GROUP, f"❌ **Upload Failed:** `{str(e)}`")
        print(f"Error during media upload: {e}")

    finally:
        gc.collect()


async def get_msg(userbot, sender, edit_id, msg_link, i, message):
    try:
        # Sanitize the message link
        msg_link = msg_link.split("?single")[0]
        chat, msg_id = None, None
        saved_channel_ids = load_saved_channel_ids()
        size_limit = 2 * 1024 * 1024 * 1024  # 1.99 GB size limit
        file = ''
        edit = ''
        # Extract chat and message ID for valid Telegram links
        if 't.me/c/' in msg_link or 't.me/b/' in msg_link:
            parts = msg_link.split("/")
            if 't.me/b/' in msg_link:
                chat = parts[-2]
                msg_id = int(parts[-1]) + i # fixed bot problem 
            else:
                chat = int('-100' + parts[parts.index('c') + 1])
                msg_id = int(parts[-1]) + i

            if chat in saved_channel_ids:
                await app.edit_message_text(
                    message.chat.id, edit_id,
                    "This channel is protected By **__╰‿╯ ҡσℓเ ⚝__💀**.\Kya Be... Hamara Hi Content Nikalega 🌝 Kahi Or Try Kar 😘"
                )
                return
            
        elif '/s/' in msg_link: # fixed story typo
            edit = await app.edit_message_text(sender, edit_id, "Story Link Dictected...")
            if userbot is None:
                await edit.edit("Login in bot save stories...")     
                return
            parts = msg_link.split("/")
            chat = parts[3]
            
            if chat.isdigit():   # this is for channel stories
                chat = f"-100{chat}"
            
            msg_id = int(parts[-1])
            await download_user_stories(userbot, chat, msg_id, edit, sender)
            await edit.delete(2)
            return
        
        else:
            edit = await app.edit_message_text(sender, edit_id, "Public link detected...🌝")
            chat = msg_link.split("t.me/")[1].split("/")[0]
            msg_id = int(msg_link.split("/")[-1])
            await copy_message_with_chat_id(app, userbot, sender, chat, msg_id, edit)
            await edit.delete(2)
            return
            
        # Fetch the target message
        msg = await userbot.get_messages(chat, msg_id)
        if not msg or msg.service or msg.empty:
            return

        target_chat_id = user_chat_ids.get(message.chat.id, message.chat.id)
        topic_id = None
        if '/' in str(target_chat_id):
            target_chat_id, topic_id = map(int, target_chat_id.split('/', 1))

        # Handle different message types
        if msg.media == MessageMediaType.WEB_PAGE_PREVIEW:
            await clone_message(app, msg, target_chat_id, topic_id, edit_id, LOG_GROUP)
            return

        if msg.text:
            await clone_text_message(app, msg, target_chat_id, topic_id, edit_id, LOG_GROUP)
            return

        if msg.sticker:
            await handle_sticker(app, msg, target_chat_id, topic_id, edit_id, LOG_GROUP)
            return
        
        # Handle file media (photo, document, video)
        file_size = get_message_file_size(msg)

        file_name = await get_media_filename(msg)
        edit = await app.edit_message_text(sender, edit_id, "**>Downloading...Darling 😉**")

        # Download media
        file = await userbot.download_media(
            msg,
            file_name=file_name,            
            progress_args=("╔══━⚡️ Downloading ⚡️━══╗\n", edit, time.time()),
            progress=progress_bar
        )
        
        gc.collect()

        caption = await get_final_caption(msg, sender)

        # Rename file
        file = await rename_file(file, sender)
        if msg.audio:
            result = await app.send_audio(target_chat_id, file, caption=caption, reply_to_message_id=topic_id)
            if LOG_GROUP and result:
                await result.forward(LOG_GROUP)
            await edit.delete(1)
            return
        
        if msg.voice:
            result = await app.send_voice(target_chat_id, file, reply_to_message_id=topic_id)
            if LOG_GROUP and result:
                await result.forward(LOG_GROUP)
            await edit.delete(1)
            return

        if msg.photo:
            result = await app.send_photo(target_chat_id, file, caption=caption, reply_to_message_id=topic_id)
            if LOG_GROUP and result:
                await result.forward(LOG_GROUP)
            await edit.delete(1)
            return

        # Upload media
        if file_size > size_limit and (free_check == 1 or pro is None):
            await edit.delete()
            await split_and_upload_file(app, sender, target_chat_id, file, caption, topic_id)
            return
        elif file_size > size_limit:
            await handle_large_file(file, sender, edit, caption)
        else:
            await upload_media(sender, target_chat_id, file, caption, edit, topic_id)

    except (ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid):
        await app.edit_message_text(sender, edit_id, "🌚 First do /login & then send me the Link again send /guide for more help")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        if file and os.path.exists(file):
            try:
                os.remove(file)
            except:
                pass
        if edit:
            await edit.delete(1)
        gc.collect()
        

async def clone_message(app, msg, target_chat_id, topic_id, edit_id, log_group):
    edit = await app.edit_message_text(target_chat_id, edit_id, "Cloning...")
    devgaganin = await app.send_message(target_chat_id, msg.text.markdown, reply_to_message_id=topic_id)
    if log_group and devgaganin:
        await devgaganin.forward(log_group)
    await edit.delete()


async def clone_text_message(app, msg, target_chat_id, topic_id, edit_id, log_group):
    edit = await app.edit_message_text(target_chat_id, edit_id, "Cloning text message...")
    devgaganin = await app.send_message(target_chat_id, msg.text.markdown, reply_to_message_id=topic_id)
    if log_group and devgaganin:
        await devgaganin.forward(log_group)
    await edit.delete()


async def handle_sticker(app, msg, target_chat_id, topic_id, edit_id, log_group):
    edit = await app.edit_message_text(target_chat_id, edit_id, "Handling sticker...")
    result = await app.send_sticker(target_chat_id, msg.sticker.file_id, reply_to_message_id=topic_id)
    if log_group and result:
        await result.forward(log_group)
    await edit.delete()


async def get_media_filename(msg):
    if msg.document:
        return msg.document.file_name or "Document_By_@TEAM_AxxxS_BOT.txt"
    if msg.video:
        return msg.video.file_name or "Video_By_@TEAM_AxxxS_BOT.mp4"
    if msg.audio:
        return msg.audio.file_name or "Audio_By_@TEAM_AxxxS_BOT.mp3"
    if msg.photo:
        return "Image_By_@TEAM_AxxxS_BOT.jpg"
    return "File_By_@TEAM_AxxxS_BOT.dat"


def get_message_file_size(msg):
    if msg.document:
        return msg.document.file_size
    if msg.photo:
        return msg.photo.file_size
    if msg.video:
        return msg.video.file_size
    return 1


async def get_final_caption(msg, sender):
    original_caption = msg.caption.markdown if msg.caption else ""
    custom_caption = get_user_caption_preference(sender)
    final_caption = f"{original_caption}\n\n{custom_caption}" if custom_caption else original_caption
    final_caption = re.sub(r'@\w+', '@TEAM_AxxxS_BOT', final_caption)
    final_caption = re.sub(r'https?://\S+|www\.\S+', 'https://t.me/SRC_PRO', final_caption)

    replacements = load_replacement_words(sender)
    for word, replace_word in replacements.items():
        final_caption = final_caption.replace(word, replace_word)

    return final_caption.strip() if final_caption else None


async def download_user_stories(userbot, chat_id, msg_id, edit, sender):
    try:
        story = await userbot.get_stories(chat_id, msg_id)
        if not story:
            await edit.edit("No story available for this user.")
            return  
        if not story.media:
            await edit.edit("The story doesn't contain any media.")
            return
        await edit.edit("Downloading Story...")
        file_path = await userbot.download_media(story)
        print(f"Story downloaded: {file_path}")
        if story.media:
            await edit.edit("Uploading Story...")
            if story.media == MessageMediaType.VIDEO:
                await app.send_video(sender, file_path)
            elif story.media == MessageMediaType.DOCUMENT:
                await app.send_document(sender, file_path)
    except Exception as e:
        print(f"Story Error: {e}")
        
