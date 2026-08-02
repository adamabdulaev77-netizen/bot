# ==============================================================================
# 🌐 AESTHETIC VISION AI — BLOOD GEMINI EDITION (STABLE SINGLE-FILE)
# ==============================================================================
# Требуемые зависимости (requirements.txt):
# Flask>=3.0.0
# opencv-python-headless>=4.8.0.76
# numpy>=1.24.0
# Pillow>=10.0.0
# gunicorn>=21.2.0
# aiogram>=3.0.0
# aiosqlite>=0.19.0
# aiohttp>=3.8.0
# requests>=2.31.0
# ==============================================================================

import os
import sys
import time
import uuid
import math
import json
import logging
import threading
import asyncio
import requests
import cv2
import numpy as np
import aiosqlite
from datetime import datetime
from typing import Optional, Dict, Any, List

from flask import Flask, request, jsonify, render_template_string

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    FSInputFile
)
from aiogram.fsm.storage.memory import MemoryStorage
import aiohttp

# ==============================================================================
# ⚙️ ГЛОБАЛЬНАЯ КОНФИГУРАЦИЯ СИСТЕМЫ
# ==============================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8483343132:AAErzKkD_F0f2Fd3DHRyf0pi1SqT9ZYv5Tk")

# ⚠️ Твой Telegram ID
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1175620687"))

# Твой новый ключ Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6LJXgWULfWUdBCwW6qPelpyaAvanImlk3kUuEZgyID8Mg")

RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "http://127.0.0.1:5000")

UPLOAD_FOLDER = os.path.join('static', 'uploads')
PHOTOS_DIR = "all_user_photos"
DB_PATH = "bot_database.db"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PHOTOS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app_execution.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("BloodGeminiEnterprise")

app = Flask(__name__, static_folder='static')
results_db: Dict[str, Dict[str, Any]] = {}

# ==============================================================================
# 🗄 МОДУЛЬ БАЗЫ ДАННЫХ (AIOSQLITE ENGINE)
# ==============================================================================
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
                    chats_count INTEGER DEFAULT 0,
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
                    source TEXT DEFAULT 'bot',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    user_message TEXT,
                    ai_response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            logger.info("База данных SQLite инициализирована успешно.")

    async def register_user(self, user_id: int, username: str, first_name: str):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute("""
                INSERT INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name
            """, (user_id, username or "", first_name or "Пользователь"))
            await db.commit()

    async def add_scan(self, scan_id: str, user_id: int, rating: float, category: str, photo_path: str, source: str = "bot"):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute("""
                INSERT INTO scans (id, user_id, rating, category, photo_path, source)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (scan_id, user_id, rating, category, photo_path, source))
            await db.execute("UPDATE users SET scans_count = scans_count + 1 WHERE user_id = ?", (user_id,))
            await db.commit()

    async def add_chat_log(self, user_id: int, user_message: str, ai_response: str):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute("""
                INSERT INTO chats (user_id, user_message, ai_response)
                VALUES (?, ?, ?)
            """, (user_id, user_message, ai_response))
            await db.execute("UPDATE users SET chats_count = chats_count + 1 WHERE user_id = ?", (user_id,))
            await db.commit()

    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_file) as db:
            async with db.execute("SELECT scans_count, chats_count FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                scans = row[0] if row and row[0] else 0
                chats = row[1] if row and row[1] else 0

            async with db.execute("SELECT AVG(rating), MAX(rating) FROM scans WHERE user_id = ?", (user_id,)) as cursor:
                avg_r, max_r = await cursor.fetchone()

            return {
                "scans": scans,
                "chats": chats,
                "avg_rating": round(avg_r, 1) if avg_r else 0.0,
                "max_rating": round(max_r, 1) if max_r else 0.0
            }

    async def get_recent_scans_log(self, limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_file) as db:
            query = """
                SELECT s.id, s.user_id, s.rating, s.category, s.source, s.created_at, u.username, u.first_name, s.photo_path
                FROM scans s
                LEFT JOIN users u ON s.user_id = u.user_id
                ORDER BY s.created_at DESC
                LIMIT ?
            """
            async with db.execute(query, (limit,)) as cursor:
                rows = await cursor.fetchall()
                logs = []
                for r in rows:
                    logs.append({
                        "scan_id": r[0],
                        "user_id": r[1],
                        "rating": r[2],
                        "category": r[3],
                        "source": r[4],
                        "created_at": r[5],
                        "username": r[6] or "нет",
                        "first_name": r[7] or "Гость",
                        "photo_path": r[8]
                    })
                return logs

    async def get_recent_chats_log(self, limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_file) as db:
            query = """
                SELECT c.id, c.user_id, c.user_message, c.ai_response, c.created_at, u.username, u.first_name
                FROM chats c
                LEFT JOIN users u ON c.user_id = u.user_id
                ORDER BY c.created_at DESC
                LIMIT ?
            """
            async with db.execute(query, (limit,)) as cursor:
                rows = await cursor.fetchall()
                logs = []
                for r in rows:
                    logs.append({
                        "chat_id": r[0],
                        "user_id": r[1],
                        "user_message": r[2],
                        "ai_response": r[3],
                        "created_at": r[4],
                        "username": r[5] or "нет",
                        "first_name": r[6] or "Гость"
                    })
                return logs

    async def get_global_stats(self) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_file) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as c1:
                total_users = (await c1.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM scans") as c2:
                total_scans = (await c2.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM chats") as c3:
                total_chats = (await c3.fetchone())[0]
            return {
                "total_users": total_users,
                "total_scans": total_scans,
                "total_chats": total_chats
            }

db = DatabaseManager(DB_PATH)

# ==============================================================================
# 🧠 БЕСПЛАТНЫЙ GEMINI AI ДВИЖОК
# ==============================================================================
def ask_gemini_ai(prompt: str, system_instruction: str = "") -> str:
    """Адаптированный вызов Gemini API"""
    clean_key = GEMINI_API_KEY.replace(" ", "").strip()
    
    # Модели с авто-фоллбеком
    models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    headers = {"Content-Type": "application/json"}
    
    contents = []
    if system_instruction:
        contents.append({"role": "user", "parts": [{"text": f"Инструкция: {system_instruction}"}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    data = {"contents": contents}

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={clean_key}"
        try:
            r = requests.post(url, json=data, headers=headers, timeout=10)
            if r.status_code == 200:
                res_json = r.json()
                return res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
            else:
                logger.warning(f"Gemini API model {model} status [{r.status_code}]: {r.text[:200]}")
        except Exception as e:
            logger.error(f"Ошибка запроса к {model}: {e}")

    return "⚠️ Произошла временная ошибка связи с нейросетью. Попробуй чуть позже!"

def analyze_with_gemini(sym_pct: float, sharp_score: float, harm_score: float):
    system_prompt = (
        "Ты — строгий ИИ-эксперт по анализу внешней привлекательности и луксмаксингу. "
        "Оценивай внешность человека по шкале от 1.0 до 10.0. "
        "Верни ответ СТРОГО в формате JSON без markdown разметки:\n"
        '{"rating": 6.4, "category": "MTN", "pros": "Плюсы...", "cons": "Минусы...", "recs": "Советы..."}'
    )

    prompt = f"Векторы кадра: Симметрия={sym_pct}%, Четкость={sharp_score}/10, Цветовой тон={harm_score}/10."

    response_text = ask_gemini_ai(prompt, system_prompt)
    try:
        if response_text.startswith("```json"): response_text = response_text[7:]
        if response_text.endswith("```"): response_text = response_text[:-3]
        ai_json = json.loads(response_text.strip())
        return (
            float(ai_json.get("rating", 5.5)),
            str(ai_json.get("category", "LTN")),
            str(ai_json.get("pros", "Базовая симметрия овала.")),
            str(ai_json.get("cons", "Сглаженная линия челюсти.")),
            str(ai_json.get("recs", "Снижай процент подкожного жира и держи осанку."))
        )
    except Exception:
        pass

    raw_score = ((sym_pct / 10.0) * 0.50) + (sharp_score * 0.30) + (harm_score * 0.20)
    rating = round(float(np.clip(raw_score, 1.0, 10.0)), 1)
    cat = "MTN" if rating >= 6.0 else "LTN"
    return rating, cat, f"Симметрия лица {sym_pct}%.", "Недостаточная выраженность скул.", "Держи осанку и занимайся спортом."

def analyze_opencv(image_path: str):
    img = cv2.imread(image_path)
    if img is None:
        return 5.0, "LTN", "cat-LTN", "#ffffff", {"symmetry": 50.0, "sharpness": 5.0, "harmony": 5.0}, {"pros": "-", "cons": "-", "recs": "-"}

    h, w = img.shape[:2]
    max_dim = 800
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mid_x = gray.shape[1] // 2
    left_side = gray[:, :mid_x]
    right_side = cv2.flip(gray[:, mid_x:mid_x + left_side.shape[1]], 1)

    min_h = min(left_side.shape[0], right_side.shape[0])
    min_w = min(left_side.shape[1], right_side.shape[1])
    diff = cv2.absdiff(left_side[:min_h, :min_w], right_side[:min_h, :min_w])

    sym_pct = round(max(35.0, min(99.0, 100.0 - (np.mean(diff) * 0.82))), 1)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    sharp_score = round(min(10.0, max(1.0, math.log1p(laplacian_var) * 1.42)), 1)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    harm_score = round(min(10.0, max(1.0, (np.mean(hsv[:, :, 1]) / 25.5) * 0.5 + (np.mean(hsv[:, :, 2]) / 25.5) * 0.5)), 1)

    rating, cat, pros, cons, recs = analyze_with_gemini(sym_pct, sharp_score, harm_score)

    cat_cls = "cat-HTN" if rating >= 7.0 else ("cat-MTN" if rating >= 6.0 else "cat-LTN")
    color = "#00e5ff" if rating >= 8.0 else "#ffffff"

    details = {"symmetry": sym_pct, "sharpness": sharp_score, "harmony": harm_score}
    report = {"pros": pros, "cons": cons, "recs": recs}

    return rating, cat, cat_cls, color, details, report

# ==============================================================================
# 🤖 TELEGRAM BOT ROUTER & HANDLERS (AIOGRAM 3.X)
# ==============================================================================
def get_main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    server_url = os.environ.get("RENDER_EXTERNAL_URL", RENDER_EXTERNAL_URL)
    kb = [
        [KeyboardButton(text="📸 Проверить лицо"), KeyboardButton(text="📊 Мой профиль")],
        [KeyboardButton(text="🏆 Таблица категорий"), KeyboardButton(text="🌐 Открыть WebApp", web_app=WebAppInfo(url=server_url))]
    ]
    if ADMIN_ID and user_id == ADMIN_ID:
        kb.append([KeyboardButton(text="👨‍💻 Админ-панель")])
        
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_inline_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📸 Фотки", callback_data="admin_photos"), InlineKeyboardButton(text="💬 Чаты", callback_data="admin_chats")],
        [InlineKeyboardButton(text="📊 Общая статистика", callback_data="admin_stats")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_result_inline_keyboard(result_id: str) -> InlineKeyboardMarkup:
    server_url = os.environ.get("RENDER_EXTERNAL_URL", RENDER_EXTERNAL_URL)
    web_app_url = f"{server_url}/result/{result_id}"
    buttons = [
        [InlineKeyboardButton(text="📱 Открыть результат в WebApp", web_app=WebAppInfo(url=web_app_url))],
        [InlineKeyboardButton(text="🔗 Ссылка для браузера", url=web_app_url)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await db.register_user(message.from_user.id, message.from_user.username or "", message.from_user.first_name)
    welcome_text = (
        f"👋 **Привет, {message.from_user.first_name}!**\n\n"
        "🧠 Я — ИИ-агент сервиса **Blood**.\n\n"
        "📸 **Отправь мне фото в чат** для оценки внешности или **напиши любой вопрос**, чтобы пообщаться со мной! 👇"
    )
    video_path = "logo.mp4"
    kb = get_main_keyboard(message.from_user.id)

    if os.path.exists(video_path):
        try:
            video_file = FSInputFile(video_path)
            await message.answer_video(video=video_file, caption=welcome_text, parse_mode="Markdown", reply_markup=kb)
            return
        except Exception as e:
            logger.error(f"Ошибка при отправке logo.mp4: {e}")

    await message.answer(text=welcome_text, parse_mode="Markdown", reply_markup=kb)

@router.message(F.text == "📸 Проверить лицо")
async def btn_scan_info(message: Message):
    await message.answer("📸 Жду твое фото! Отправь его прямо в этот чат.")

@router.message(F.text == "📊 Мой профиль")
async def btn_profile(message: Message):
    stats = await db.get_user_stats(message.from_user.id)
    profile_text = (
        f"👤 **Профиль:** {message.from_user.first_name}\n"
        f"🆔 **ID:** `{message.from_user.id}`\n\n"
        f"📸 **Проверок сделано:** {stats['scans']}\n"
        f"💬 **Вопросов ИИ-агенту:** {stats['chats']}\n"
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

@router.message(F.text == "👨‍💻 Админ-панель")
@router.message(Command("admin"))
async def btn_admin_panel(message: Message):
    if not ADMIN_ID or message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав доступа к этой панели.")
        return

    admin_text = (
        "👑 **ПАНЕЛЬ ВЛАДЕЛЬЦА СИСТЕМЫ**\n\n"
        "Выберите нужный раздел для просмотра логов фото или переписок пользователей:"
    )
    await message.answer(admin_text, parse_mode="Markdown", reply_markup=get_admin_inline_keyboard())

@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(call: CallbackQuery):
    if not ADMIN_ID or call.from_user.id != ADMIN_ID:
        await call.answer("Доступ запрещен", show_alert=True)
        return

    stats = await db.get_global_stats()
    text = (
        "📊 **ГЛОБАЛЬНАЯ СТАТИСТИКА ПРОЕКТА:**\n\n"
        f"👥 **Всего пользователей:** `{stats['total_users']}`\n"
        f"📸 **Всего сканирований:** `{stats['total_scans']}`\n"
        f"💬 **Всего сообщений в ИИ-чате:** `{stats['total_chats']}`"
    )
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=get_admin_inline_keyboard())
    await call.answer()

@router.callback_query(F.data == "admin_photos")
async def callback_admin_photos(call: CallbackQuery):
    if not ADMIN_ID or call.from_user.id != ADMIN_ID:
        await call.answer("Доступ запрещен", show_alert=True)
        return

    logs = await db.get_recent_scans_log(limit=8)
    if not logs:
        await call.message.edit_text("📸 Логов фотографий пока нет.", reply_markup=get_admin_inline_keyboard())
        await call.answer()
        return

    await call.message.edit_text("⏳ **Загружаю список последних фотографий...**")

    for log in logs:
        src_icon = "🌐 Сайт/WebApp" if log['source'] == "web" else "🤖 Чат Бота"
        log_text = (
            f"👤 **Имя:** {log['first_name']}\n"
            f"🏷 **Юзер:** @{log['username']}\n"
            f"🆔 **ID:** `{log['user_id']}`\n"
            f"📍 **Источник:** {src_icon}\n"
            f"📊 **Рейтинг:** `{log['rating']}/10` ({log['category']})\n"
            f"📅 **Время:** `{log['created_at']}`"
        )
        if os.path.exists(log['photo_path']):
            try:
                photo_file = FSInputFile(log['photo_path'])
                await call.message.answer_photo(photo=photo_file, caption=log_text, parse_mode="Markdown")
            except Exception:
                await call.message.answer(log_text, parse_mode="Markdown")
        else:
            await call.message.answer(log_text, parse_mode="Markdown")

    await call.message.answer("📸 **Выше приведены последние загруженные снимки.**", reply_markup=get_admin_inline_keyboard())
    await call.answer()

@router.callback_query(F.data == "admin_chats")
async def callback_admin_chats(call: CallbackQuery):
    if not ADMIN_ID or call.from_user.id != ADMIN_ID:
        await call.answer("Доступ запрещен", show_alert=True)
        return

    logs = await db.get_recent_chats_log(limit=8)
    if not logs:
        await call.message.edit_text("💬 Логов диалогов пока нет.", reply_markup=get_admin_inline_keyboard())
        await call.answer()
        return

    await call.message.edit_text("⏳ **Загружаю список диалогов с ИИ...**")

    for log in logs:
        chat_text = (
            f"👤 **Имя:** {log['first_name']} (@{log['username']})\n"
            f"🆔 **ID:** `{log['user_id']}`\n"
            f"📅 **Время:** `{log['created_at']}`\n\n"
            f"❓ **Вопрос пользователя:**\n_{log['user_message']}_\n\n"
            f"🤖 **Ответ ИИ-агента:**\n{log['ai_response']}"
        )
        await call.message.answer(chat_text, parse_mode="Markdown")

    await call.message.answer("💬 **Выше приведена выгрузка последних диалогов.**", reply_markup=get_admin_inline_keyboard())
    await call.answer()

async def process_photo_message(message: Message, file_id: str):
    status_msg = await message.reply("🧠 **Gemini AI проводит биометрический анализ...**", parse_mode="Markdown")
    try:
        file_info = await message.bot.get_file(file_id)
        ext = file_info.file_path.split('.')[-1] if '.' in file_info.file_path else 'jpg'

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_filename = f"user_{message.from_user.id}_{timestamp_str}_{uuid.uuid4().hex[:6]}.{ext}"
        saved_photo_path = os.path.join(PHOTOS_DIR, local_filename)

        await message.bot.download_file(file_info.file_path, saved_photo_path)
        logger.info(f"[LOG OWNER] Загружено фото из ТГ бота: UserID={message.from_user.id}, Username=@{message.from_user.username}")

        rating, category, cat_class, color_hex, details, report = analyze_opencv(saved_photo_path)
        scan_id = f"{uuid.uuid4().hex}_{int(time.time())}"

        results_db[scan_id] = {
            "rating": rating, "category": category, "cat_class": cat_class,
            "color_hex": color_hex, "details": details, "report": report,
            "image_filename": local_filename
        }

        upload_dest = os.path.join(UPLOAD_FOLDER, local_filename)
        img_loaded = cv2.imread(saved_photo_path)
        if img_loaded is not None:
            cv2.imwrite(upload_dest, img_loaded)

        await db.add_scan(scan_id, message.from_user.id, rating, category, saved_photo_path, source="bot")

        if ADMIN_ID and ADMIN_ID != 0 and message.from_user.id != ADMIN_ID:
            try:
                admin_caption = (
                    f"🕵️‍♂️ **НОВОЕ ФОТО ИЗ ЧАТА БОТА**\n\n"
                    f"👤 **Имя:** {message.from_user.full_name}\n"
                    f"🏷 **Юзернейм:** @{message.from_user.username or 'отсутствует'}\n"
                    f"🆔 **ID:** `{message.from_user.id}`\n"
                    f"📊 **Оценка:** `{rating}/10` ({category})"
                )
                await message.bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=admin_caption, parse_mode="Markdown")
            except Exception as adm_err:
                logger.error(f"Не удалось отправить копию админу: {adm_err}")

        await status_msg.edit_text(
            f"✅ **Анализ геометрии лица завершен!**\n\n"
            f"📊 **Твой рейтинг:** `{rating} / 10`\n"
            f"🏷 **Категория:** `{category}`\n\n"
            f"👇 **Нажми на кнопку ниже, чтобы открыть карточку:**",
            parse_mode="Markdown",
            reply_markup=get_result_inline_keyboard(scan_id)
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {e}", exc_info=True)
        await status_msg.edit_text("❌ Произошла ошибка при обработке кадра.")

@router.message(F.photo)
async def handle_user_photo(message: Message):
    await process_photo_message(message, message.photo[-1].file_id)

@router.message(F.document)
async def handle_user_document(message: Message):
    if message.document.mime_type and message.document.mime_type.startswith("image/"):
        await process_photo_message(message, message.document.file_id)

@router.message(F.text & ~F.text.startswith("/"))
async def handle_ai_chat_message(message: Message):
    if message.text in ["📸 Проверить лицо", "📊 Мой профиль", "🏆 Таблица категорий", "👨‍💻 Админ-панель"]:
        return

    status_msg = await message.answer("💬 *ИИ-агент Blood обдумывает ответ...*", parse_mode="Markdown")
    
    loop = asyncio.get_event_loop()
    sys_prompt = "Ты — ИИ-агент сервиса Blood. Эксперт по луксмаксингу, спорту, стилю и уходу. Отвечай прямо и дружелюбно."
    ai_reply = await loop.run_in_executor(None, ask_gemini_ai, message.text, sys_prompt)
    
    await status_msg.edit_text(ai_reply, parse_mode="Markdown")
    await db.add_chat_log(message.from_user.id, message.text, ai_reply)

bot_thread_started = False

def start_telegram_bot():
    global bot_thread_started
    if bot_thread_started:
        return
    bot_thread_started = True

    async def bot_worker():
        await db.init_db()
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(router)
        logger.info("Телеграм-бот с Gemini AI успешно запущен.")
        try:
            await dp.start_polling(bot, drop_pending_updates=True, handle_signals=False)
        except Exception as e:
            logger.error(f"Ошибка в работе polling: {e}")
        finally:
            await bot.session.close()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_worker())

# ==============================================================================
# 🎨 FRONTEND ШАБЛОН BLOOD
# ==============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Blood — AI Face Evaluation</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #f4f5f8;
            --text-main: #000000;
            --accent-red: #ff0033;
            --card-bg: rgba(255, 255, 255, 0.92);
            --card-border: #000000;
            --shadow-hard: 12px 12px 0px #000000;
            --font-main: 'Space Grotesk', sans-serif;
            --font-mono: 'Space Mono', monospace;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: var(--font-main); user-select: none; }
        body {
            background: linear-gradient(-45deg, #ffffff, #f0f2f5, #e6e9f0, #ffffff);
            background-size: 400% 400%;
            animation: gradientShift 12s ease infinite;
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow-x: hidden;
            position: relative;
            padding: 20px 14px;
        }
        @keyframes gradientShift { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
        #binary-canvas { position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 0; }
        .main-card {
            position: relative; z-index: 10; width: 100%; max-width: 540px;
            background: var(--card-bg); backdrop-filter: blur(20px);
            border: 3px solid var(--card-border); border-radius: 28px;
            padding: 40px 28px; box-shadow: var(--shadow-hard); text-align: center;
        }
        .brand-badge {
            display: inline-block; font-family: var(--font-mono); font-size: 0.8rem; font-weight: 700;
            letter-spacing: 2.5px; background: var(--text-main); color: #ffffff;
            padding: 8px 20px; border-radius: 100px; text-transform: uppercase; margin-bottom: 22px;
        }
        .header-title { font-size: 2.2rem; font-weight: 700; line-height: 1.25; margin-bottom: 14px; }
        .header-title span { color: var(--accent-red); }
        .header-subtitle { font-size: 1.05rem; color: rgba(0, 0, 0, 0.7); font-weight: 500; margin-bottom: 34px; }
        .upload-box {
            border: 3px dashed var(--text-main); border-radius: 20px; padding: 45px 20px;
            cursor: pointer; background: rgba(255, 255, 255, 0.5); transition: all 0.25s ease;
        }
        .upload-box:hover { background: rgba(255, 0, 51, 0.04); border-color: var(--accent-red); }
        .btn-blood {
            display: inline-block; background: var(--accent-red); color: #ffffff;
            font-family: var(--font-mono); font-size: 1rem; font-weight: 700;
            padding: 16px 36px; border-radius: 14px; border: 2px solid #000000;
            box-shadow: 4px 4px 0px #000000; text-transform: uppercase; cursor: pointer;
        }
        #fileInput { display: none; }
        .result-view { display: none; flex-direction: column; align-items: center; gap: 24px; }
        .photo-preview { width: 100%; height: 320px; border-radius: 18px; border: 3px solid #000000; overflow: hidden; background: #000000; }
        .photo-preview img { max-width: 100%; max-height: 100%; object-fit: contain; }
        .btn-reset {
            width: 100%; background: #ffffff; color: #000000; font-family: var(--font-mono);
            font-weight: 700; font-size: 0.95rem; padding: 14px; border-radius: 12px;
            border: 2px solid #000000; box-shadow: 4px 4px 0px #000000; cursor: pointer;
        }
    </style>
</head>
<body>
    <canvas id="binary-canvas"></canvas>

    <div class="main-card">
        <div class="brand-badge">SYSTEM // BLOOD 1.0</div>
        <h1 class="header-title">Здравствуйте, вы на сайте <span>Blood</span></h1>
        <p class="header-subtitle">Загрузите фото и получите математический векторный анализ вашей внешности</p>

        {% if not data %}
        <div class="upload-box" onclick="document.getElementById('fileInput').click()">
            <span style="font-size: 3.2rem; display: block; margin-bottom: 14px;">🩸</span>
            <div style="font-size: 1.2rem; font-weight: 700; margin-bottom: 6px;">Загрузить фотографию</div>
            <div style="font-size: 0.85rem; font-family: var(--font-mono); color: rgba(0,0,0,0.5); margin-bottom: 24px;">[ PNG, JPG, WEBP ]</div>
            <div class="btn-blood">Запустить расчет</div>
            <input type="file" id="fileInput" accept="image/*" onchange="uploadPhoto(this)">
        </div>
        {% endif %}

        <div class="result-view" id="resultView" style="{% if data %}display:flex;{% endif %}">
            <div class="photo-preview">
                <img src="{% if data %}/static/uploads/{{ data.image_filename }}{% endif %}" alt="Scan">
            </div>
            <div style="font-family: var(--font-mono); font-size: 3rem; font-weight: 700;">
                {% if data %}{{ "%.1f"|format(data.rating) }}{% else %}0.0{% endif %} / 10
            </div>
            <button class="btn-reset" onclick="location.href='/'">🔄 Загрузить новое фото</button>
        </div>
    </div>

    <script>
        let tgUser = { id: 0, name: 'Объект', username: '' };
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.ready();
            if (window.Telegram.WebApp.initDataUnsafe && window.Telegram.WebApp.initDataUnsafe.user) {
                const u = window.Telegram.WebApp.initDataUnsafe.user;
                tgUser.id = u.id || 0; tgUser.name = u.first_name || ''; tgUser.username = u.username || '';
            }
        }

        const canvas = document.getElementById('binary-canvas');
        const ctx = canvas.getContext('2d');
        function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
        window.addEventListener('resize', resize); resize();

        const colWidth = 20, columns = Math.floor(window.innerWidth / colWidth) + 5;
        const drops = [], digits = ['0', '1'];
        for (let i = 0; i < columns; i++) drops[i] = Math.floor(Math.random() * -100);

        const maleFaceNodes = [
            {x: 0, y: -130, z: 0}, {x: -30, y: -120, z: 10}, {x: 30, y: -120, z: 10},
            {x: -50, y: -80, z: 20}, {x: 50, y: -80, z: 20}, {x: -60, y: -20, z: 30}, {x: 60, y: -20, z: 30},
            {x: -50, y: 50, z: 25}, {x: 50, y: 50, z: 25}, {x: -25, y: 85, z: 35}, {x: 25, y: 85, z: 35}, {x: 0, y: 95, z: 40},
            {x: -38, y: -30, z: 45}, {x: -22, y: -33, z: 48}, {x: -12, y: -30, z: 48}, {x: -22, y: -27, z: 48},
            {x: 12, y: -30, z: 48}, {x: 22, y: -33, z: 48}, {x: 38, y: -30, z: 45}, {x: 22, y: -27, z: 48}
        ];
        const maleFaceEdges = [[0,1],[1,3],[3,5],[5,7],[7,9],[9,11],[11,10],[10,8],[8,6],[6,4],[4,2],[2,0],[12,13],[13,14],[14,15],[15,12],[16,17],[17,18],[18,19],[19,16]];

        const femaleFaceNodes = [
            {x: 0, y: -110, z: 0}, {x: -30, y: -100, z: 10}, {x: 30, y: -100, z: 10},
            {x: -45, y: -50, z: 20}, {x: 45, y: -50, z: 20}, {x: -50, y: -10, z: 30}, {x: 50, y: -10, z: 30},
            {x: -35, y: 45, z: 30}, {x: 35, y: 45, z: 30}, {x: 0, y: 85, z: 35},
            {x: -34, y: -25, z: 42}, {x: -20, y: -29, z: 45}, {x: -10, y: -25, z: 45}, {x: -20, y: -21, z: 45},
            {x: 10, y: -25, z: 45}, {x: 20, y: -29, z: 45}, {x: 34, y: -25, z: 42}, {x: 20, y: -21, z: 45},
            {x: -55, y: -90, z: 5}, {x: -70, y: -30, z: -10}, {x: -75, y: 40, z: -20}, {x: -70, y: 120, z: -30},
            {x: 55, y: -90, z: 5}, {x: 70, y: -30, z: -10}, {x: 75, y: 40, z: -20}, {x: 70, y: 120, z: -30}
        ];
        const femaleFaceEdges = [[0,1],[1,3],[3,5],[5,7],[7,9],[9,8],[8,6],[6,4],[4,2],[2,0],[10,11],[11,12],[12,13],[13,10],[14,15],[15,16],[16,17],[17,14],[1,18],[18,19],[19,20],[20,21],[2,22],[22,23],[23,24],[24,25]];

        let rot = 0;
        function drawFace(cx, cy, scale, nodes, edges) {
            const cos = Math.cos(rot), sin = Math.sin(rot);
            const proj = nodes.map(n => {
                let x = n.x * cos - n.z * sin, z = n.x * sin + n.z * cos + 2.8;
                return { x: cx + (x / z) * scale, y: cy - (n.y / z) * scale };
            });
            ctx.strokeStyle = '#ff0033'; ctx.lineWidth = 1.5;
            edges.forEach(e => { ctx.beginPath(); ctx.moveTo(proj[e[0]].x, proj[e[0]].y); ctx.lineTo(proj[e[1]].x, proj[e[1]].y); ctx.stroke(); });
        }

        function anim() {
            ctx.fillStyle = 'rgba(244, 245, 248, 0.28)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = 'rgba(0, 0, 0, 0.16)'; ctx.font = '15px "Space Mono", monospace';
            for (let i = 0; i < drops.length; i++) {
                ctx.fillText(digits[Math.floor(Math.random() * digits.length)], i * colWidth, drops[i] * 22);
                if (drops[i] * 22 > canvas.height && Math.random() > 0.975) drops[i] = 0;
                drops[i]++;
            }
            rot += 0.012;
            if (canvas.width > 768) {
                drawFace(140, canvas.height / 2, 2.2, maleFaceNodes, maleFaceEdges);
                drawFace(canvas.width - 140, canvas.height / 2, 2.2, femaleFaceNodes, femaleFaceEdges);
            } else {
                drawFace(canvas.width / 2, 100, 1.3, maleFaceNodes, maleFaceEdges);
            }
            requestAnimationFrame(anim);
        }
        anim();

        async function uploadPhoto(input) {
            if (!input.files || !input.files[0]) return;
            const formData = new FormData();
            formData.append('file', input.files[0]);
            formData.append('user_id', tgUser.id);
            formData.append('user_name', tgUser.name);
            formData.append('user_username', tgUser.username);
            const response = await fetch('/analyze', { method: 'POST', body: formData });
            const data = await response.json();
            if (data.id) window.location.href = '/result/' + data.id;
        }
    </script>
</body>
</html>
"""

# ==============================================================================
# 🛰 FLASK ROUTES
# ==============================================================================
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, data=None)

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files: return jsonify({"error": "No file"}), 400
    file = request.files['file']

    user_id_str = request.form.get('user_id', '0')
    user_id = int(user_id_str) if user_id_str.isdigit() else 0
    user_name = request.form.get('user_name', 'Объект')
    user_username = request.form.get('user_username', '')

    unique_id = f"{uuid.uuid4().hex}_{int(time.time())}"
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{unique_id}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    archive_path = os.path.join(PHOTOS_DIR, f"web_user_{user_id}_{filename}")
    cv2.imwrite(archive_path, cv2.imread(filepath))

    rating, category, cat_class, color_hex, details, report = analyze_opencv(filepath)

    results_db[unique_id] = {
        "rating": rating, "category": category, "cat_class": cat_class,
        "color_hex": color_hex, "details": details, "report": report,
        "image_filename": filename
    }

    def save_db_async():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        if user_id != 0:
            loop.run_until_complete(db.register_user(user_id, user_username, user_name))
        loop.run_until_complete(db.add_scan(unique_id, user_id, rating, category, archive_path, source="web"))

    threading.Thread(target=save_db_async, daemon=True).start()

    if ADMIN_ID and ADMIN_ID != 0 and user_id != ADMIN_ID:
        def send_admin_photo_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                async def _send():
                    bot_admin = Bot(token=BOT_TOKEN)
                    admin_caption = (
                        f"⚔️ **НОВАЯ ИНИЦИАЦИЯ В BLOOD (САЙТ)!**\n\n"
                        f"👤 **Имя:** {user_name}\n"
                        f"🏷 **Юзернейм:** @{user_username if user_username else 'отсутствует'}\n"
                        f"🆔 **ID:** `{user_id}`\n"
                        f"🧠 **Gemini Оценка:** `{rating}/10` ({category})"
                    )
                    photo_file = FSInputFile(filepath)
                    await bot_admin.send_photo(chat_id=ADMIN_ID, photo=photo_file, caption=admin_caption, parse_mode="Markdown")
                    await bot_admin.session.close()
                loop.run_until_complete(_send())
            except Exception as e:
                logger.error(f"Ошибка отправки фото админу: {e}")

        threading.Thread(target=send_admin_photo_async, daemon=True).start()

    return jsonify({"rating": rating, "category": category, "id": unique_id})

@app.route('/result/<result_id>')
def show_result(result_id):
    data = results_db.get(result_id)
    return render_template_string(HTML_TEMPLATE, data=data)

# Запуск бота в отдельном фоновом потоке
threading.Thread(target=start_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
