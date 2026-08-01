import os
import sys
import uuid
import logging
import asyncio
import aiosqlite
from typing import Optional, Dict, Any
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    FSInputFile
)
import aiohttp

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8483343132:AAErzKkD_F0f2Fd3DHRyf0pi1SqT9ZYv5Tk")
FLASK_SERVER_URL = os.environ.get("FLASK_SERVER_URL", "https://bot-c88n.onrender.com")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

DB_PATH = "bot_database.db"
PHOTOS_DIR = "all_user_photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AestheticBot")

class DatabaseManager:
    def __init__(self, db_file: str):
        self.db_file = db_file

    async def init_db(self):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    scans_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS scans (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    rating REAL,
                    category TEXT,
                    photo_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def register_user(self, user_id: int, username: Optional[str], first_name: str):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute("""
                INSERT INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name
            """, (user_id, username, first_name))
            await db.commit()

    async def add_scan(self, scan_id: str, user_id: int, rating: float, category: str, photo_path: str):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute("""
                INSERT INTO scans (id, user_id, rating, category, photo_path)
                VALUES (?, ?, ?, ?, ?)
            """, (scan_id, user_id, rating, category, photo_path))
            await db.execute("UPDATE users SET scans_count = scans_count + 1 WHERE user_id = ?", (user_id,))
            await db.commit()

    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_file) as db:
            async with db.execute("SELECT scans_count FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                scans = row[0] if row else 0

            async with db.execute("SELECT AVG(rating), MAX(rating) FROM scans WHERE user_id = ?", (user_id,)) as cursor:
                avg_r, max_r = await cursor.fetchone()

            return {
                "scans": scans,
                "avg_rating": round(avg_r, 1) if avg_r else 0.0,
                "max_rating": round(max_r, 1) if max_r else 0.0
            }

db = DatabaseManager(DB_PATH)

def get_main_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="📸 Проверить лицо"), KeyboardButton(text="📊 Мой профиль")],
        [KeyboardButton(text="🏆 Таблица категорий"), KeyboardButton(text="🌐 Открыть WebApp", web_app=WebAppInfo(url=FLASK_SERVER_URL))]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_result_inline_keyboard(result_id: str) -> InlineKeyboardMarkup:
    web_app_url = f"{FLASK_SERVER_URL}/result/{result_id}"
    buttons = [
        [InlineKeyboardButton(text="📱 Открыть результат в WebApp", web_app=WebAppInfo(url=web_app_url))],
        [InlineKeyboardButton(text="🔗 Ссылка для браузера", url=web_app_url)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await db.register_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    welcome_text = (
        f"👋 **Привет, {message.from_user.first_name}!**\n\n"
        "🔥 Я — ИИ-агент по векторному анализу привлекательности и геометрии лица.\n\n"
        "📸 **Отправь мне фото в чат** или нажми на кнопку **«Открыть WebApp»** ниже! 👇"
    )
    video_path = "logo.mp4"
    if os.path.exists(video_path):
        video_file = FSInputFile(video_path)
        try:
            await message.answer_animation(animation=video_file, caption=welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
        except Exception:
            await message.answer_video(video=video_file, caption=welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
    else:
        await message.answer(text=welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

@router.message(F.text == "📸 Проверить лицо")
async def btn_scan_info(message: Message):
    await message.answer("📸 Жду твое фото! Отправь его прямо в этот чат.")

@router.message(F.text == "📊 Мой профиль")
async def btn_profile(message: Message):
    stats = await db.get_user_stats(message.from_user.id)
    profile_text = (
        f"👤 **Профиль:** {message.from_user.first_name}\n"
        f"🆔 **ID:** `{message.from_user.id}`\n\n"
        f"📈 **Проверок сделано:** {stats['scans']}\n"
        f"⭐ **Средний балл:** `{stats['avg_rating']} / 10`\n"
        f"🔥 **Максимальный балл:** `{stats['max_rating']} / 10`"
    )
    await message.answer(profile_text, parse_mode="Markdown")

@router.message(F.text == "🏆 Таблица категорий")
async def btn_categories(message: Message):
    categories_text = (
        "🏆 **КАТЕГОРИИ И РЕЙТИНГ ЛУКСМАКСИНГА:**\n\n"
        "🔴 **1.0 - 2.9** — `SUB 3`\n"
        "🟠 **3.0 - 4.9** — `SUB 5`\n"
        "🟡 **5.0 - 5.9** — `LTN` (Low Tier Normal)\n"
        "🟢 **6.0 - 6.9** — `MTN` (Mid Tier Normal)\n"
        "❇️ **7.0 - 7.9** — `HTN` (High Tier Normal)\n"
        "💎 **8.0 - 9.9** — `CHAD`\n"
        "👑 **10.0** — `TRUE ADAM` (Золотое Сечение)"
    )
    await message.answer(categories_text, parse_mode="Markdown")

async def process_photo_message(message: Message, file_id: str):
    status_msg = await message.reply("🔄 **[1/3] ИИ загружает фото и высчитывает векторы...**", parse_mode="Markdown")
    try:
        file_info = await message.bot.get_file(file_id)
        ext = file_info.file_path.split('.')[-1] if '.' in file_info.file_path else 'jpg'
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_filename = f"user_{message.from_user.id}_{timestamp_str}_{uuid.uuid4().hex[:6]}.{ext}"
        saved_photo_path = os.path.join(PHOTOS_DIR, local_filename)

        await message.bot.download_file(file_info.file_path, saved_photo_path)

        if ADMIN_ID and ADMIN_ID != 0:
            try:
                admin_caption = (
                    f"🕵️‍♂️ **НОВОЕ ФОТО ПОЛЬЗОВАТЕЛЯ**\n\n"
                    f"👤 **Имя:** {message.from_user.full_name}\n"
                    f"🏷 **Юзернейм:** @{message.from_user.username or 'отсутствует'}\n"
                    f"🆔 **ID:** `{message.from_user.id}`\n"
                    f"📁 **Файл:** `{local_filename}`"
                )
                await message.bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=admin_caption, parse_mode="Markdown")
            except Exception as adm_err:
                logger.error(f"Не удалось отправить копию админу: {adm_err}")

        async with aiohttp.ClientSession() as session:
            with open(saved_photo_path, 'rb') as f:
                form_data = aiohttp.FormData()
                form_data.add_field('file', f, filename=local_filename)
                
                async with session.post(f"{FLASK_SERVER_URL}/analyze", data=form_data) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        scan_id = data.get("id")
                        rating = float(data.get("rating", 5.0))
                        category = data.get("category", "LTN")
                        
                        await db.add_scan(scan_id, message.from_user.id, rating, category, saved_photo_path)
                        
                        await status_msg.edit_text(
                            f"✅ **Анализ геометрии лица завершен!**\n\n"
                            f"📊 **Твой рейтинг:** `{rating} / 10`\n"
                            f"🏷 **Категория:** `{category}`\n\n"
                            f"👇 **Нажми на кнопку ниже, чтобы открыть интерактивную карточку:**",
                            parse_mode="Markdown",
                            reply_markup=get_result_inline_keyboard(scan_id)
                        )
                    else:
                        await status_msg.edit_text("❌ Ошибка при передаче фотографии на сервер.")
    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {e}", exc_info=True)
        await status_msg.edit_text("❌ Произошла ошибка связи с сервером.")

@router.message(F.photo)
async def handle_user_photo(message: Message):
    await process_photo_message(message, message.photo[-1].file_id)

@router.message(F.document)
async def handle_user_document(message: Message):
    if message.document.mime_type and message.document.mime_type.startswith("image/"):
        await process_photo_message(message, message.document.file_id)

async def main():
    await db.init_db()
    # Прямое подключение без локального прокси
    bot = Bot(token=BOT_TOKEN)
    logger.info("Бот запущен на сервере Render без прокси.")

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())