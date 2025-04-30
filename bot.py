import logging
import os
import yt_dlp
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_links = {}  # ذخیره لینک‌ها به ازای ID کاربر

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("سلام! لینک یوتیوب رو بفرست تا کیفیت‌ها رو انتخاب کنی.")

@dp.message_handler()
async def handle_link(message: types.Message):
    url = message.text
    if "youtube.com" in url or "youtu.be" in url:
        user_links[message.from_user.id] = url
        formats = get_video_formats(url)
        if not formats:
            await message.reply("خطا در دریافت کیفیت‌ها.")
            return

        kb = InlineKeyboardMarkup()
        for f in formats:
            kb.add(InlineKeyboardButton(f"{f['format_note']} ({f['ext']})", callback_data=f"{f['format_id']}"))
        await message.reply("یکی از کیفیت‌ها رو انتخاب کن:", reply_markup=kb)
    else:
        await message.reply("فعلاً فقط لینک یوتیوب رو بفرست.")

@dp.callback_query_handler()
async def process_callback(callback_query: types.CallbackQuery):
    format_id = callback_query.data
    user_id = callback_query.from_user.id
    url = user_links.get(user_id)

    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(user_id, f"درحال دانلود کیفیت {format_id}...")

    file_path = download_youtube_video(url, format_id)
    if not file_path:
        await bot.send_message(user_id, "خطا در دانلود.")
        return

    if os.path.getsize(file_path) > 48 * 1024 * 1024:
        await bot.send_message(user_id, "حجم این ویدیو بالای 50MB هست. لینک دانلودش اینه:")
        await bot.send_message(user_id, f"فایل: {file_path}")
    else:
        with open(file_path, 'rb') as f:
            await bot.send_video(user_id, f)

    os.remove(file_path)

def get_video_formats(url):
    try:
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = [f for f in info['formats'] if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
            formats = sorted(formats, key=lambda x: int(x['height']) if x.get('height') else 0, reverse=True)
            return formats
    except Exception as e:
        print("Error fetching formats:", e)
        return []

def download_youtube_video(url, format_id):
    try:
        ydl_opts = {
            'format': format_id,
            'outtmpl': 'video.%(ext)s',
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except Exception as e:
        print("Error downloading:", e)
        return None

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)