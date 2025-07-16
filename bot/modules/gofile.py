import os
import time
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from bot import Bot  # ייבוא מ-bot/__init__.py או מקביל בסניף wzv3
from bot.config import *  # ייבוא הגדרות כמו DOWNLOAD_DIR, AUTHORIZED_CHATS
from bot.helpers.utils import get_readable_file_size, get_readable_time

# הגדרות GoFile
GOFILE_API_URL = "https://api.gofile.io"
EXPIRE_TIME = 864000000  # 10 ימים במילישניות

# פונקציה לקבלת שרת GoFile
async def get_gofile_server():
    try:
        response = requests.get(f"{GOFILE_API_URL}/getServer")
        response.raise_for_status()
        data = response.json()
        if data["status"] == "ok":
            return data["data"]["server"]
        return None
    except Exception as e:
        return None

# פונקציה להעלאת קובץ ל-GoFile
async def upload_to_gofile(file_path, expire_time=EXPIRE_TIME):
    server = await get_gofile_server()
    if not server:
        return None, "Failed to get GoFile server"
    
    url = f"https://{server}.gofile.io/uploadFile"
    try:
        with open(file_path, "rb") as file:
            files = {"file": file}
            data = {"expire": expire_time}
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            result = response.json()
            if result["status"] == "ok":
                return result["data"]["downloadPage"], None
            return None, "Upload failed"
    except Exception as e:
        return None, f"Upload error: {e}"

# פקודת /gofile
@Client.on_message(filters.command(["gofile"]) & filters.chat(AUTHORIZED_CHATS))
async def gofile_upload(client: Bot, message: Message):
    if not message.reply_to_message or not (message.reply_to_message.document or message.reply_to_message.text):
        await message.reply("Please reply to a file or a link with /gofile.")
        return

    start_time = time.time()
    user_id = message.from_user.id
    file_name = None
    file_size = 0
    file_path = None

    # טיפול בקובץ או קישור
    if message.reply_to_message.document:
        file = message.reply_to_message.document
        file_name = file.file_name
        file_size = file.file_size
        file_path = await client.download_media(file, file_name=f"{DOWNLOAD_DIR}/{file_name}")
    elif message.reply_to_message.text:
        # הנחה: קישור לקובץ. ניתן להרחיב עם לוגיקת הורדה כמו ב-mirror.py
        await message.reply("Link upload not supported yet. Please upload a file.")
        return

    if not file_path:
        await message.reply("Failed to download the file.")
        return

    # יצירת הודעת סטטוס בקבוצה
    status_msg = await message.reply(
        f"**Uploading to GoFile**\n"
        f"**File Name**: {file_name}\n"
        f"**Size**: {get_readable_file_size(file_size)}\n"
        f"**Status**: Starting upload..."
    )

    # העלאה ל-GoFile
    download_url, error = await upload_to_gofile(file_path)

    # מחיקת הקובץ המקומי
    try:
        os.remove(file_path)
    except:
        pass

    # עדכון הודעת הסטטוס
    if download_url:
        elapsed_time = get_readable_time(time.time() - start_time)
        status_text = (
            f"**Upload Complete**\n"
            f"**File Name**: {file_name}\n"
            f"**Size**: {get_readable_file_size(file_size)}\n"
            f"**Time Taken**: {elapsed_time}\n"
            f"**Download Link**: Sent to your DM\n"
            f"**Expires**: In 10 days"
        )
        await status_msg.edit(status_text)

        # שליחת הקישור בפרטי
        try:
            await client.send_message(
                chat_id=user_id,
                text=f"**GoFile Upload**\n**File**: {file_name}\n**Link**: {download_url}\n**Expires**: In 10 days"
            )
        except Exception as e:
            await status_msg.edit(f"{status_text}\n**Error**: Failed to send link to DM: {e}")
    else:
        await status_msg.edit(f"**Upload Failed**\n**File**: {file_name}\n**Error**: {error}")
