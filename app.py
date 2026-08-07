# ==============================================================================
# 🌐 AESTHETIC VISION AI — TRUE ADAM MATRIX ULTIMATE SINGLE-FILE
# ==============================================================================
# Requirements (requirements.txt):
# Flask>=3.0.0
# opencv-python-headless>=4.8.0.76
# numpy>=1.24.0
# Pillow>=10.0.0
# gunicorn>=21.2.0
# aiogram>=3.0.0
# aiosqlite>=0.19.0
# aiohttp>=3.8.0
# requests>=2.31.0
# gTTS>=2.5.0
# edge-tts>=6.1.9
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
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

# ==============================================================================
# ⚙️ GLOBAL SYSTEM CONFIGURATION
# ==============================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8483343132:AAErzKkD_F0f2Fd3DHRyf0pi1SqT9ZYv5Tk")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1175620687"))

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "http://127.0.0.1:5000")

UPLOAD_FOLDER = os.path.join('static', 'uploads')
PHOTOS_DIR = "all_user_photos"
VOICE_DIR = os.path.join('static', 'voice')
DB_PATH = "bot_database.db"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(VOICE_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app_execution.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("TrueAdamEnterprise")

app = Flask(__name__, static_folder='static')
results_db: Dict[str, Dict[str, Any]] = {}

class ScanStates(StatesGroup):
    waiting_for_gender = State()
    waiting_for_photo = State()

PUFFINESS_GUIDE_TEXT = (
    "🧊 **ПРОТОКОЛ: КАК УБРАТЬ ОТЁКИ ЗА 15 МИНУТ (ЛИМФОДРЕНАЖ)**\n\n"
    "1️⃣ **Контрастное умывание:**\n"
    "Поочередно умывайся теплой и ледяной водой (по 10 секунд, 5 циклов). Это моментально активирует микроциркуляцию.\n\n"
    "2️⃣ **Лимфодренажный массаж (Гуаша / Пальцы):**\n"
    "Двигайся строго по лимфотоку: от центра подбородка к мочкам ушей, от крыльев носа к вискам и вниз по шее к ключицам.\n\n"
    "3️⃣ **Водный и натриевый баланс:**\n"
    "Отёки появляются из-за задержки воды. Исключи соль, соусы и фастфуд на ночь. Выпей 500 мл чистой воды сразу после пробуждения.\n\n"
    "4️⃣ **Зарядка и осанка:**\n"
    "Сделай 20 легких прыжков на пятках и растяни шею. Это запустит лимфатическую систему организма."
)

# ==============================================================================
# 🗄 DATABASE MANAGER (AIOSQLITE ENGINE)
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
                    gender TEXT DEFAULT 'male',
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

    async def add_scan(self, scan_id: str, user_id: int, rating: float, category: str, gender: str, photo_path: str, source: str = "bot"):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute("""
                INSERT INTO scans (id, user_id, rating, category, gender, photo_path, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (scan_id, user_id, rating, category, gender, photo_path, source))
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
                SELECT s.id, s.user_id, s.rating, s.category, s.gender, s.source, s.created_at, u.username, u.first_name, s.photo_path
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
                        "gender": r[4] or "male",
                        "source": r[5],
                        "created_at": r[6],
                        "username": r[7] or "нет",
                        "first_name": r[8] or "Гость",
                        "photo_path": r[9]
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
# 🎙 VOICE SYNTHESIS MODULE (EDGE-TTS / GTTS)
# ==============================================================================
async def create_voice_note(text: str) -> Optional[str]:
    """Generates a natural male voice note file"""
    clean_text = text.replace('*', '').replace('_', '').replace('`', '').replace('#', '')
    if len(clean_text) > 400:
        clean_text = clean_text[:400] + "..."

    filename = f"voice_{uuid.uuid4().hex[:8]}.mp3"
    filepath = os.path.join(VOICE_DIR, filename)

    if EDGE_TTS_AVAILABLE:
        try:
            communicate = edge_tts.Communicate(clean_text, voice="ru-RU-DmitryNeural")
            await communicate.save(filepath)
            return filepath
        except Exception as e:
            logger.warning(f"Edge-TTS synthesis warning, falling back: {e}")

    if GTTS_AVAILABLE:
        try:
            loop = asyncio.get_running_loop()
            def _gtts_save():
                tts = gTTS(text=clean_text, lang='ru', slow=False)
                tts.save(filepath)
            await loop.run_in_executor(None, _gtts_save)
            return filepath
        except Exception as e:
            logger.error(f"GTTS error: {e}")

    return None

# ==============================================================================
# 🧠 GROQ AI ENGINE
# ==============================================================================
def ask_groq_ai(prompt: str, system_instruction: str = "") -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
        "Content-Type": "application/json"
    }
    
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it", "llama-3.2-3b-preview"]

    for model_name in models:
        data = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7
        }
        try:
            r = requests.post(GROQ_API_URL, json=data, headers=headers, timeout=10)
            if r.status_code == 200:
                res_json = r.json()
                return res_json["choices"][0]["message"]["content"].strip()
            else:
                logger.warning(f"Groq model {model_name} status [{r.status_code}]: {r.text[:150]}")
        except Exception as e:
            logger.error(f"Error calling Groq model {model_name}: {e}")

    return "⚠️ Произошла ошибка связи с нейросетью."

def analyze_with_groq_deep(sym_pct: float, sharp_score: float, harm_score: float, gender: str = "male"):
    gender_title = "МУЖЧИНА" if gender == "male" else "ЖЕНЩИНА"
    
    system_prompt = (
        f"Ты — главный ИИ-эксперт сервиса TRUE ADAM (@TrueAdam_robot) по биометрическому разбору лиц, Золотому Сечению и луксмаксингу. "
        f"Объект анализа: {gender_title}.\n"
        "Оценивай внешность строго, объективно по шкале от 1.0 до 10.0.\n"
        "Верни ответ СТРОГО в формате JSON без markdown разметки:\n"
        '{\n'
        '  "rating": 7.2,\n'
        '  "category": "HTN",\n'
        '  "eyes_score": 7.5,\n'
        '  "cheekbones_score": 7.0,\n'
        '  "jaw_score": 7.8,\n'
        '  "hair_score": 8.0,\n'
        '  "skin_score": 7.2,\n'
        '  "gender_score": 7.6,\n'
        '  "pros": "1. Высокая симметрия овала лица (88%).\\n2. Четко выраженная челюстная дуга.\\n3. Отличный цветовой баланс и контраст кадра.",\n'
        '  "cons": "1. Легкая асимметрия подбородка.\\n2. Сглаженная резкость деталей средней трети.",\n'
        '  "recs": "1. ДЕФАТТИНГ: Снизь процент жира в организме до 11-13% для выделения скул.\\n2. МЬЮИНГ: Сохраняй правильное положение языка у нёба.",\n'
        '  "potential": "8.7 (CHAD)"\n'
        '}'
    )

    prompt = f"Векторные данные кадра: Симметрия={sym_pct}%, Индекс резкости={sharp_score}/10, Цветовой тон={harm_score}/10. Пол={gender_title}."

    response_text = ask_groq_ai(prompt, system_prompt)
    try:
        if response_text.startswith("```json"): response_text = response_text[7:]
        if response_text.endswith("```"): response_text = response_text[:-3]
        ai_json = json.loads(response_text.strip())
        return (
            float(ai_json.get("rating", 6.0)),
            str(ai_json.get("category", "MTN")),
            float(ai_json.get("eyes_score", 7.0)),
            float(ai_json.get("cheekbones_score", 6.5)),
            float(ai_json.get("jaw_score", 7.0)),
            float(ai_json.get("hair_score", 7.5)),
            float(ai_json.get("skin_score", 7.0)),
            float(ai_json.get("gender_score", 7.2)),
            str(ai_json.get("pros", "1. Базовая симметрия овала.\n2. Удовлетворительный баланс пропорций.")),
            str(ai_json.get("cons", "1. Сглаженная линия челюсти.\n2. Недостаточный рельеф скуловых костей.")),
            str(ai_json.get("recs", "1. Снижай процент подкожного жира.\n2. Держи осанку и выполняй мьюинг.")),
            str(ai_json.get("potential", "8.0 (CHAD)"))
        )
    except Exception:
        pass

    raw_score = ((sym_pct / 10.0) * 0.50) + (sharp_score * 0.30) + (harm_score * 0.20)
    rating = round(float(np.clip(raw_score, 1.0, 10.0)), 1)
    cat = "MTN" if rating >= 6.0 else "LTN"
    
    pros = f"1. Высокая симметрия овала ({sym_pct}%).\n2. Хороший цветовой баланс ({harm_score}/10)."
    cons = f"1. Сглаженная резкость деталей ({sharp_score}/10).\n2. Недостаточная выраженность скул."
    recs = "1. Снижай процент подкожного жира.\n2. Делай массаж Гуаша и исправь осанку."
    pot = f"{min(10.0, rating + 1.5):.1f} (HTN/CHAD)"

    return rating, cat, rating, rating, rating, rating, rating, rating, pros, cons, recs, pot

def analyze_opencv(image_path: str, gender: str = "male"):
    img = cv2.imread(image_path)
    if img is None:
        return 5.0, "LTN", "cat-LTN", "#ffffff", {
            "symmetry": 50.0, "sharpness": 5.0, "harmony": 5.0,
            "eyes": 5.0, "cheekbones": 5.0, "jaw": 5.0, "hair": 5.0, "skin": 5.0, "gender_feat": 5.0
        }, {
            "pros": "1. Базовый баланс кадра.", "cons": "1. Не удалось прочитать детали кадра.", "recs": "1. Сделайте более четкий снимок.", "potential": "7.0 (MTN)"
        }

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

    rating, cat, e_s, c_s, j_s, h_s, s_s, g_s, pros, cons, recs, potential = analyze_with_groq_deep(sym_pct, sharp_score, harm_score, gender)

    if rating < 3.0: cat_cls, color = "cat-SUB3", "#ff3333"
    elif rating < 5.0: cat_cls, color = "cat-SUB5", "#ff8833"
    elif rating < 6.0: cat_cls, color = "cat-LTN", "#e6e6e6"
    elif rating < 7.0: cat_cls, color = "cat-MTN", "#cccccc"
    elif rating < 8.0: cat_cls, color = "cat-HTN", "#ffffff"
    elif rating < 10.0: cat_cls, color = "cat-CHAD", "#00e5ff"
    else: cat_cls, color = "cat-TRUE_ADAM", "#ffd700"

    details = {
        "symmetry": sym_pct,
        "sharpness": sharp_score,
        "harmony": harm_score,
        "eyes": e_s,
        "cheekbones": c_s,
        "jaw": j_s,
        "hair": h_s,
        "skin": s_s,
        "gender_feat": g_s
    }
    report = {"pros": pros, "cons": cons, "recs": recs, "potential": potential}

    return rating, cat, cat_cls, color, details, report

# ==============================================================================
# 🤖 TELEGRAM BOT ROUTER & HANDLERS
# ==============================================================================
def get_main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    server_url = os.environ.get("RENDER_EXTERNAL_URL", RENDER_EXTERNAL_URL)
    kb = [
        [KeyboardButton(text="📸 Проверить лицо"), KeyboardButton(text="📊 Мой профиль")],
        [KeyboardButton(text="🧊 Гайд: Как убрать отёки"), KeyboardButton(text="🌐 Открыть WebApp", web_app=WebAppInfo(url=server_url))]
    ]
    if ADMIN_ID and user_id == ADMIN_ID:
        kb.append([KeyboardButton(text="👨‍💻 Админ-панель")])
        
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_gender_inline_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🚹 Мужской анализ", callback_data="gender_male")],
        [InlineKeyboardButton(text="🚺 Женский анализ", callback_data="gender_female")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_inline_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📸 Фотки", callback_data="admin_photos"), InlineKeyboardButton(text="💬 Чаты", callback_data="admin_chats")],
        [InlineKeyboardButton(text="📊 Общая статистика", callback_data="admin_stats")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_result_inline_keyboard(result_id: str, rating: float, category: str) -> InlineKeyboardMarkup:
    server_url = os.environ.get("RENDER_EXTERNAL_URL", RENDER_EXTERNAL_URL)
    web_app_url = f"{server_url}/result/{result_id}"
    share_text = f"🔥 Мой генетический индекс внешности в TRUE ADAM: {rating}/10 ({category})! Проверь себя в @TrueAdam_robot:"
    share_url = f"https://t.me/share/url?url={web_app_url}&text={requests.utils.quote(share_text)}"

    buttons = [
        [InlineKeyboardButton(text="📱 Открыть подробную карточку", web_app=WebAppInfo(url=web_app_url))],
        [InlineKeyboardButton(text="📲 Поделиться результатом", url=share_url)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await db.register_user(message.from_user.id, message.from_user.username or "", message.from_user.first_name)
    welcome_text = (
        f"👋 **Привет, {message.from_user.first_name}!**\n\n"
        "🔥 Я — ИИ-агент TRUE ADAM по векторному анализу привлекательности, пропорций и геометрии лица.\n\n"
        "📸 **Нажми «📸 Проверить лицо»** или **задай любой вопрос** прямо в чат! 👇\n\n"
        "🏷 Bot: `@TrueAdam_robot`"
    )
    video_path = "logo.mp4"
    kb = get_main_keyboard(message.from_user.id)

    if os.path.exists(video_path):
        try:
            video_file = FSInputFile(video_path)
            await message.answer_video(
                video=video_file,
                caption=welcome_text,
                parse_mode="Markdown",
                reply_markup=kb
            )
            return
        except Exception as e:
            logger.error(f"Ошибка при отправке logo.mp4: {e}")

    await message.answer(text=welcome_text, parse_mode="Markdown", reply_markup=kb)

@router.message(F.text == "📸 Проверить лицо")
async def btn_scan_info(message: Message, state: FSMContext):
    await state.set_state(ScanStates.waiting_for_gender)
    await message.answer(
        "🧬 **Выберите пол объекта для настройки стандартов пропорций:**",
        reply_markup=get_gender_inline_keyboard()
    )

@router.callback_query(F.data.startswith("gender_"))
async def callback_select_gender(call: CallbackQuery, state: FSMContext):
    selected_gender = "male" if call.data == "gender_male" else "female"
    await state.update_data(gender=selected_gender)
    await state.set_state(ScanStates.waiting_for_photo)
    
    gender_str = "Мужской" if selected_gender == "male" else "Женский"
    await call.message.edit_text(
        f"✅ Выбран пол: **{gender_str}**.\n\n"
        "📸 **Отправьте портретное фото в чат** для получения глубокого разбора."
    )
    await call.answer()

@router.message(F.text == "🧊 Гайд: Как убрать отёки")
async def btn_puffiness_guide(message: Message):
    await message.answer(PUFFINESS_GUIDE_TEXT, parse_mode="Markdown")
    voice_file = await create_voice_note("Прямо сейчас слушай главный протокол против отёков лица: умывайся ледяной водой, пей чистую воду и делай лимфодренажный массаж Гуаша.")
    if voice_file and os.path.exists(voice_file):
        try:
            v_input = FSInputFile(voice_file)
            await message.answer_voice(voice=v_input)
        except Exception as e:
            logger.error(f"Ошибка отправки голосового гайда: {e}")

@router.message(F.text == "📊 Мой профиль")
async def btn_profile(message: Message):
    stats = await db.get_user_stats(message.from_user.id)
    profile_text = (
        f"👤 **Профиль:** {message.from_user.first_name}\n"
        f"🆔 **ID:** `{message.from_user.id}`\n\n"
        f"📈 **Проверок сделано:** {stats['scans']}\n"
        f"💬 **Вопросов ИИ:** {stats['chats']}\n"
        f"⭐ **Средний балл:** `{stats['avg_rating']} / 10`\n"
        f"🔥 **Максимальный балл:** `{stats['max_rating']} / 10`\n\n"
        f"🏷 Bot: `@TrueAdam_robot`"
    )
    await message.answer(profile_text, parse_mode="Markdown")

@router.message(F.text == "👨‍💻 Админ-панель")
@router.message(Command("admin"))
async def btn_admin_panel(message: Message):
    if not ADMIN_ID or message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав доступа к этой панели.")
        return

    admin_text = (
        "👑 **ПАНЕЛЬ ВЛАДЕЛЬЦА СИСТЕМЫ**\n\n"
        "Выберите раздел для просмотра логов фотографий или истории переписок с ИИ:"
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

    await call.message.answer("📸 **Выше приведена выгрузка последних снимков.**", reply_markup=get_admin_inline_keyboard())
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

async def process_photo_message(message: Message, file_id: str, state: FSMContext):
    user_data = await state.get_data()
    gender = user_data.get("gender", "male")
    await state.clear()

    status_msg = await message.reply("🧠 **Groq AI проводит биометрический глубокий анализ...**", parse_mode="Markdown")
    try:
        file_info = await message.bot.get_file(file_id)
        ext = file_info.file_path.split('.')[-1] if '.' in file_info.file_path else 'jpg'

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_filename = f"user_{message.from_user.id}_{timestamp_str}_{uuid.uuid4().hex[:6]}.{ext}"
        saved_photo_path = os.path.join(PHOTOS_DIR, local_filename)

        await message.bot.download_file(file_info.file_path, saved_photo_path)
        logger.info(f"[LOG OWNER] Загружено фото из ТГ бота: UserID={message.from_user.id}, Gender={gender}")

        rating, category, cat_class, color_hex, details, report = analyze_opencv(saved_photo_path, gender)
        scan_id = f"{uuid.uuid4().hex}_{int(time.time())}"

        results_db[scan_id] = {
            "rating": rating,
            "category": category,
            "cat_class": cat_class,
            "color_hex": color_hex,
            "details": details,
            "report": report,
            "gender": gender,
            "image_filename": local_filename
        }

        upload_dest = os.path.join(UPLOAD_FOLDER, local_filename)
        img_loaded = cv2.imread(saved_photo_path)
        if img_loaded is not None:
            cv2.imwrite(upload_dest, img_loaded)

        await db.add_scan(scan_id, message.from_user.id, rating, category, gender, saved_photo_path, source="bot")

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

        gender_label = "Мужественность" if gender == "male" else "Женственность"

        detailed_text = (
            f"✅ **ПОЛНОЦЕННЫЙ БИОМЕТРИЧЕСКИЙ РАЗБОР:**\n\n"
            f"📊 **Твой рейтинг:** `{rating} / 10` ({category})\n"
            f"💎 **Потенциал:** `{report.get('potential', '8.5 CHAD')}`\n\n"
            f"👁 **Глаза:** `{details.get('eyes', rating)} / 10`\n"
            f"🦴 **Скулы:** `{details.get('cheekbones', rating)} / 10`\n"
            f"📐 **Челюсть:** `{details.get('jaw', rating)} / 10`\n"
            f"💇‍♂️ **Волосы:** `{details.get('hair', rating)} / 10`\n"
            f"🧴 **Кожа:** `{details.get('skin', rating)} / 10`\n"
            f"⚡ **{gender_label}:** `{details.get('gender_feat', rating)} / 10`\n\n"
            f"🔥 **ГЕНЕТИЧЕСКИЕ ПЛЮСЫ:**\n{report['pros']}\n\n"
            f"❌ **ЗОНЫ ДЕСИНХРОНИЗАЦИИ:**\n{report['cons']}\n\n"
            f"💡 **ПОШАГОВЫЙ ПЛАН ПРОКАЧКИ:**\n{report['recs']}\n\n"
            f"🏷 `@TrueAdam_robot`"
        )

        await status_msg.edit_text(
            detailed_text,
            parse_mode="Markdown",
            reply_markup=get_result_inline_keyboard(scan_id, rating, category)
        )

        summary_voice_text = f"Анализ завершен. Ваш рейтинг {rating} из 10. Категория {category}. Подробные векторные оценки смотрите в карточке."
        voice_file = await create_voice_note(summary_voice_text)
        if voice_file and os.path.exists(voice_file):
            try:
                v_input = FSInputFile(voice_file)
                await message.answer_voice(voice=v_input)
            except Exception as ve:
                logger.error(f"Ошибка отправки голосового файла: {ve}")

    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {e}", exc_info=True)
        await status_msg.edit_text("❌ Произошла ошибка при обработке кадра.")

@router.message(F.photo)
async def handle_user_photo(message: Message, state: FSMContext):
    await process_photo_message(message, message.photo[-1].file_id, state)

@router.message(F.document)
async def handle_user_document(message: Message, state: FSMContext):
    if message.document.mime_type and message.document.mime_type.startswith("image/"):
        await process_photo_message(message, message.document.file_id, state)

@router.message(F.text & ~F.text.startswith("/"))
async def handle_ai_chat_message(message: Message):
    if message.text in ["📸 Проверить лицо", "📊 Мой профиль", "🧊 Гайд: Как убрать отёки", "👨‍💻 Админ-панель"]:
        return

    status_msg = await message.answer("💬 *ИИ-агент обдумывает ответ...*", parse_mode="Markdown")
    
    loop = asyncio.get_event_loop()
    sys_prompt = "Ты — ИИ-агент сервиса TRUE ADAM (@TrueAdam_robot). Эксперт по луксмаксингу, спорту, стилю и уходу. Отвечай прямо, коротко и содержательно."
    ai_reply = await loop.run_in_executor(None, ask_groq_ai, message.text, sys_prompt)
    
    await status_msg.edit_text(ai_reply, parse_mode="Markdown")
    await db.add_chat_log(message.from_user.id, message.text, ai_reply)

    voice_file = await create_voice_note(ai_reply)
    if voice_file and os.path.exists(voice_file):
        try:
            v_input = FSInputFile(voice_file)
            await message.answer_voice(voice=v_input)
        except Exception as ve:
            logger.error(f"Ошибка отправки голосового ответа: {ve}")

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
        
        await bot.delete_webhook(drop_pending_updates=True)
        
        logger.info("Телеграм-бот с Groq AI запущен.")
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
# 🎨 TRUE ADAM LANDING PAGE & INTEGRATED SCANNER FRONTEND
# ==============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <meta name="theme-color" content="#07070a" />
  <title>TRUE ADAM — Looksmaxxing Guide & Biometric AI | @TrueAdam_Robot</title>

  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js" crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js" crossorigin="anonymous"></script>
  <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800;900&family=Rajdhani:wght@500;700&family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">

  <style>
    :root {
      --bg: #050507;
      --bg-soft: #0b0b10;
      --card: rgba(255,255,255,.055);
      --card-strong: rgba(255,255,255,.09);
      --line: rgba(255,255,255,.11);
      --text: #f6f7fb;
      --muted: #a4a7b5;
      --cyan: #6cf5ff;
      --blue: #6580ff;
      --violet: #a56cff;
      --pink: #ff7bd5;
      --success: #7dffb2;
      --gold: #ffd700;
      --radius: 28px;
      --shadow: 0 24px 80px rgba(0,0,0,.45);
    }

    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; scrollbar-width: thin; scrollbar-color: rgba(108,245,255,.65) #07070a; }
    ::selection { background: rgba(108,245,255,.22); color: #fff; }
    ::-webkit-scrollbar { width: 9px; }
    ::-webkit-scrollbar-track { background: #07070a; }
    ::-webkit-scrollbar-thumb { background: linear-gradient(var(--cyan), var(--violet)); border-radius: 20px; border: 2px solid #07070a; }

    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at 15% 15%, rgba(101,128,255,.14), transparent 28%),
        radial-gradient(circle at 85% 8%, rgba(165,108,255,.15), transparent 30%),
        radial-gradient(circle at 60% 75%, rgba(108,245,255,.08), transparent 35%),
        var(--bg);
      color: var(--text);
      overflow-x: hidden;
      cursor: default;
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
      background-size: 64px 64px;
      mask-image: linear-gradient(to bottom, rgba(0,0,0,.8), transparent 90%);
      z-index: -3;
    }

    a { color: inherit; text-decoration: none; }
    button { font: inherit; }

    .noise {
      position: fixed; inset: 0; opacity: .035; pointer-events: none; z-index: 20;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.45'/%3E%3C/svg%3E");
    }

    .orb {
      position: fixed; width: 420px; aspect-ratio: 1; border-radius: 50%; filter: blur(80px); opacity: .14; pointer-events: none; z-index: -2; transition: transform .2s linear;
    }
    .orb.one { background: var(--blue); top: 12%; left: -180px; }
    .orb.two { background: var(--violet); right: -180px; bottom: 8%; }

    .container { width: min(1180px, calc(100% - 40px)); margin: 0 auto; }

    .nav-wrap { position: fixed; left: 0; right: 0; top: 18px; z-index: 50; display: flex; justify-content: center; }
    .nav {
      width: min(1140px, calc(100% - 28px)); min-height: 68px; padding: 10px 12px 10px 18px; display: flex; align-items: center; justify-content: space-between; gap: 20px; border: 1px solid var(--line); background: rgba(8,8,12,.72); backdrop-filter: blur(22px); border-radius: 22px; box-shadow: 0 18px 60px rgba(0,0,0,.28);
    }
    .brand { display: flex; align-items: center; gap: 12px; font-weight: 800; letter-spacing: .08em; }
    .brand-mark { width: 38px; height: 38px; border-radius: 13px; display: grid; place-items: center; background: linear-gradient(135deg, var(--cyan), var(--blue) 55%, var(--violet)); color: #050507; box-shadow: 0 0 35px rgba(108,245,255,.25); font-size: 18px; }
    .brand-copy { display: flex; flex-direction: column; line-height: 1; gap: 5px; }
    .brand-copy small { font-size: 9px; letter-spacing: .18em; color: var(--muted); font-weight: 650; }

    .nav-links { display: flex; gap: 6px; }
    .nav-links a { padding: 12px 14px; border-radius: 14px; color: var(--muted); font-size: 14px; transition: .3s ease; }
    .nav-links a:hover, .nav-links a.active { color: var(--text); background: rgba(255,255,255,.07); }

    .nav-cta, .primary, .secondary { border: 0; border-radius: 16px; cursor: pointer; transition: transform .3s ease, box-shadow .3s ease, background .3s ease; }
    .nav-cta { padding: 13px 17px; color: #07070a; font-weight: 800; background: linear-gradient(135deg, var(--cyan), #c6fbff); box-shadow: 0 10px 28px rgba(108,245,255,.2); }
    .nav-cta:hover, .primary:hover, .secondary:hover { transform: translateY(-2px); }

    .hero { min-height: 100vh; display: grid; align-items: center; padding: 130px 0 60px; position: relative; }
    .hero-grid { display: grid; grid-template-columns: 1.05fr .95fr; align-items: start; gap: 50px; }

    .eyebrow { display: inline-flex; align-items: center; gap: 10px; padding: 10px 14px; border: 1px solid var(--line); border-radius: 999px; color: #d8dbea; background: rgba(255,255,255,.04); font-size: 13px; letter-spacing: .05em; text-transform: uppercase; }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--success); box-shadow: 0 0 16px var(--success); }

    h1 { margin: 24px 0 20px; font-size: clamp(48px, 6.5vw, 92px); line-height: .92; letter-spacing: -.06em; max-width: 850px; }
    .gradient-text { background: linear-gradient(100deg, #fff 5%, var(--cyan) 43%, var(--blue) 67%, var(--violet)); -webkit-background-clip: text; color: transparent; }

    .hero p { max-width: 690px; color: var(--muted); font-size: clamp(16px, 1.8vw, 19px); line-height: 1.65; }

    .hero-actions { display: flex; gap: 14px; margin-top: 28px; flex-wrap: wrap; }
    .primary { padding: 16px 22px; background: linear-gradient(135deg, var(--cyan), var(--blue)); color: #050507; font-weight: 850; box-shadow: 0 14px 34px rgba(101,128,255,.28); }
    .secondary { padding: 16px 22px; background: rgba(255,255,255,.055); border: 1px solid var(--line); color: var(--text); }

    .micro { margin-top: 24px; display: flex; flex-wrap: wrap; gap: 18px; color: #8f93a5; font-size: 13px; }
    .micro span::before { content: "✦"; color: var(--cyan); margin-right: 8px; }

    /* SCANNER WIDGET BOX */
    .scanner-widget-card {
      border: 1px solid var(--line);
      background: rgba(12, 16, 26, 0.88);
      backdrop-filter: blur(28px);
      border-radius: 28px;
      padding: 24px;
      box-shadow: 0 24px 80px rgba(0,0,0,.6), 0 0 40px rgba(108,245,255,.12);
      text-align: center;
      position: relative;
    }

    .gender-selector { display: flex; gap: 10px; margin-bottom: 16px; justify-content: center; }
    .gender-btn {
      flex: 1; padding: 10px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.2); color: #ffffff; font-family: 'Orbitron', sans-serif; font-size: 0.8rem; font-weight: 700; cursor: pointer; border-radius: 12px; transition: all 0.3s;
    }
    .gender-btn.active { background: var(--cyan); color: #000000; box-shadow: 0 0 15px var(--cyan); }

    #scanner-wrap {
      position: relative; width: 100%; max-height: 480px; aspect-ratio: 3/4; border: 2px solid var(--line); border-radius: 18px; background: #000000; overflow: hidden; display: flex; align-items: center; justify-content: center; margin-bottom: 18px; cursor: pointer; transition: border-color 0.3s, box-shadow 0.3s;
    }
    #scanner-wrap.success-flash {
      border-color: var(--success) !important; box-shadow: 0 0 50px rgba(125,255,178,0.8), inset 0 0 20px rgba(125,255,178,0.3) !important;
    }

    .placeholder-text { color: var(--cyan); font-family: 'Orbitron', sans-serif; font-size: 0.85rem; line-height: 1.6; }
    #user-image { max-width: 100%; max-height: 100%; object-fit: contain; display: none; position: absolute; }
    #overlay-canvas { position: absolute; z-index: 5; pointer-events: none; opacity: 0; transition: opacity 0.3s ease; }

    .laser-line {
      position: absolute; top: -10px; left: 0; width: 100%; height: 4px; background: linear-gradient(90deg, transparent, var(--cyan), #ffffff, var(--cyan), transparent); box-shadow: 0 0 15px var(--cyan), 0 0 30px var(--cyan); display: none; z-index: 10;
    }
    @keyframes scanAnimation { 0% { top: 0%; } 50% { top: 100%; } 100% { top: 0%; } }
    .laser-active { display: block; animation: scanAnimation 2s ease-in-out infinite; }

    .scan-status-bar {
      background: rgba(108,245,255, 0.08); border: 1px solid var(--cyan); padding: 8px; border-radius: 10px; font-family: 'Orbitron', sans-serif; font-size: 0.75rem; color: var(--cyan); letter-spacing: 1.5px; margin-bottom: 16px; text-transform: uppercase;
    }

    .btn-blood {
      width: 100%; background: linear-gradient(135deg, var(--cyan), var(--blue)); color: #000000; font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 0.9rem; padding: 15px; border-radius: 14px; border: none; cursor: pointer; text-transform: uppercase; box-shadow: 0 0 20px rgba(108,245,255, 0.4); transition: all 0.3s;
    }
    .btn-blood:hover { background: #ffffff; box-shadow: 0 0 30px #ffffff; transform: translateY(-2px); }

    .result-screen { display: none; flex-direction: column; align-items: center; gap: 18px; }

    .gauge-box { position: relative; width: 170px; height: 180px; }
    .gauge-box svg { width: 100%; height: 100%; transform: rotate(-90deg); }
    .gauge-bg-track { fill: none; stroke: rgba(255, 255, 255, 0.08); stroke-width: 12; }
    .gauge-fill-bar {
      fill: none; stroke-width: 12; stroke-linecap: square; stroke-dasharray: 565.48; stroke-dashoffset: 565.48; transition: stroke-dashoffset 2s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .gauge-center { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; }
    .score-num { font-family: 'Orbitron', sans-serif; font-size: 3.2rem; font-weight: 900; color: #ffffff; text-shadow: 0 0 15px rgba(255, 255, 255, 0.8); }

    .category-badge {
      padding: 8px 30px; font-family: 'Orbitron', sans-serif; font-size: 1.3rem; font-weight: 900; letter-spacing: 3px; text-transform: uppercase; border: 1px solid var(--cyan); background: rgba(108,245,255, 0.1); color: var(--cyan); border-radius: 10px;
    }

    .metrics-card {
      width: 100%; background: rgba(255, 255, 255, 0.03); border: 1px solid var(--line); border-radius: 16px; padding: 16px; display: flex; flex-direction: column; gap: 10px;
    }
    .metric-row { display: flex; flex-direction: column; gap: 4px; text-align: left; }
    .metric-info { display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; }
    .track-bar { height: 6px; background: rgba(255, 255, 255, 0.08); border-radius: 3px; overflow: hidden; }
    .fill-bar { height: 100%; width: 0%; background: var(--cyan); transition: width 1.5s; }

    .report-box { width: 100%; display: flex; flex-direction: column; gap: 10px; text-align: left; }
    .report-card { background: rgba(255, 255, 255, 0.03); border: 1px solid var(--line); border-radius: 14px; padding: 14px; }
    .report-title { font-family: 'Orbitron', sans-serif; font-size: 0.8rem; font-weight: 800; margin-bottom: 4px; text-transform: uppercase; }

    .watermark-footer { margin-top: 10px; font-family: 'Orbitron', sans-serif; font-size: 0.8rem; color: var(--cyan); letter-spacing: 2px; text-shadow: 0 0 10px var(--cyan); }

    /* MARQUEE & PILLARS */
    .marquee { overflow: hidden; border-block: 1px solid var(--line); background: rgba(255,255,255,.02); transform: rotate(-1deg) scale(1.02); margin: 25px 0 70px; }
    .marquee-track { display: flex; width: max-content; animation: marquee 26s linear infinite; }
    .marquee-track span { padding: 16px 24px; font-size: 13px; letter-spacing: .16em; text-transform: uppercase; color: #c9ccda; white-space: nowrap; }
    .marquee-track i { color: var(--cyan); font-style: normal; }

    section { padding: 90px 0; }
    .section-head { display: flex; align-items: end; justify-content: space-between; gap: 24px; margin-bottom: 36px; }
    .section-head h2 { font-size: clamp(36px, 5vw, 66px); letter-spacing: -.055em; margin: 12px 0 0; line-height: 1; }
    .section-head p { color: var(--muted); max-width: 520px; line-height: 1.7; }

    .tabs-shell { padding: 14px; border: 1px solid var(--line); border-radius: 32px; background: rgba(255,255,255,.035); box-shadow: var(--shadow); backdrop-filter: blur(20px); }
    .tabs { display: flex; gap: 10px; padding: 6px; overflow-x: auto; position: relative; }
    .tab-btn { flex: 1; min-width: 140px; padding: 15px 18px; color: var(--muted); background: transparent; border: 0; border-radius: 16px; cursor: pointer; transition: .3s ease; position: relative; z-index: 2; }
    .tab-btn.active { color: var(--text); background: linear-gradient(135deg, rgba(108,245,255,.15), rgba(165,108,255,.16)); box-shadow: inset 0 0 0 1px rgba(255,255,255,.09); }

    .tab-panels { position: relative; min-height: 390px; }
    .tab-panel { display: none; grid-template-columns: .85fr 1.15fr; gap: 18px; padding: 18px 6px 6px; opacity: 0; transform: translateY(14px); }
    .tab-panel.active { display: grid; animation: panelIn .5s ease forwards; }

    .feature-main, .feature-list > div, .card, .step, .faq-item {
      border: 1px solid var(--line); background: linear-gradient(145deg, rgba(255,255,255,.07), rgba(255,255,255,.025)); backdrop-filter: blur(18px);
    }
    .feature-main { border-radius: 26px; padding: 28px; min-height: 350px; display: flex; flex-direction: column; justify-content: space-between; }
    .feature-icon { font-size: 46px; }
    .feature-main h3 { font-size: 34px; margin: 22px 0 12px; }
    .feature-main p, .feature-list p { color: var(--muted); line-height: 1.65; }
    .metric { display: flex; justify-content: space-between; align-items: end; border-top: 1px solid var(--line); padding-top: 20px; }
    .metric strong { font-size: 38px; }
    .metric span { color: var(--muted); font-size: 13px; }

    .feature-list { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
    .feature-list > div { border-radius: 24px; padding: 24px; transition: .35s ease; }
    .feature-list > div:hover { transform: translateY(-6px); background: rgba(255,255,255,.075); }
    .feature-list h4 { font-size: 20px; margin: 0 0 8px; }

    .cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
    .card { border-radius: 28px; padding: 28px; min-height: 270px; position: relative; overflow: hidden; transition: transform .35s ease, border-color .35s ease; }
    .card:hover { border-color: rgba(255,255,255,.22); transform: translateY(-5px); }
    .card-number { font-size: 12px; letter-spacing: .18em; color: var(--cyan); }
    .card h3 { font-size: 26px; margin: 38px 0 12px; }
    .card p { color: var(--muted); line-height: 1.65; }

    .roadmap { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
    .step { border-radius: 24px; padding: 24px; position: relative; overflow: hidden; }
    .step span { width: 42px; height: 42px; border-radius: 14px; display: grid; place-items: center; background: rgba(255,255,255,.075); color: var(--cyan); font-weight: 800; }
    .step h3 { margin: 38px 0 10px; font-size: 22px; }
    .step p { color: var(--muted); line-height: 1.55; font-size: 14px; }

    .manifesto {
      border: 1px solid var(--line); border-radius: 34px; padding: clamp(30px, 5vw, 70px);
      background: radial-gradient(circle at 90% 20%, rgba(165,108,255,.15), transparent 30%), radial-gradient(circle at 10% 80%, rgba(108,245,255,.12), transparent 30%), rgba(255,255,255,.035);
      text-align: center; box-shadow: var(--shadow);
    }
    .manifesto h2 { font-size: clamp(38px, 6vw, 80px); letter-spacing: -.065em; line-height: .95; margin: 0 0 22px; }
    .manifesto p { max-width: 780px; margin: 0 auto; color: var(--muted); font-size: 18px; line-height: 1.7; }

    .faq { display: grid; gap: 12px; max-width: 900px; margin: 0 auto; }
    .faq-item { border-radius: 20px; overflow: hidden; }
    .faq-q { width: 100%; border: 0; background: transparent; color: var(--text); text-align: left; padding: 22px 24px; display: flex; justify-content: space-between; gap: 20px; cursor: pointer; font-weight: 700; }
    .faq-item.open .faq-q span:last-child { transform: rotate(45deg); }
    .faq-a { max-height: 0; overflow: hidden; color: var(--muted); transition: max-height .4s ease, padding .4s ease; padding: 0 24px; line-height: 1.65; }
    .faq-item.open .faq-a { max-height: 220px; padding: 0 24px 22px; }

    footer { padding: 60px 0 35px; }
    .footer-inner { border-top: 1px solid var(--line); padding-top: 28px; display: flex; justify-content: space-between; gap: 20px; color: var(--muted); font-size: 14px; }

    .floating-telegram { position: fixed; right: 22px; bottom: 22px; z-index: 60; display: flex; align-items: center; gap: 10px; padding: 12px 18px; border-radius: 18px; color: #071016; font-weight: 850; background: linear-gradient(135deg, var(--cyan), #fff); box-shadow: 0 16px 55px rgba(108,245,255,.27); transition: .35s ease; }
    .floating-telegram:hover { transform: translateY(-5px) scale(1.02); }

    .reveal { opacity: 0; transform: translateY(28px); transition: opacity .8s ease, transform .8s ease; }
    .reveal.visible { opacity: 1; transform: translateY(0); }

    @keyframes marquee { to { transform: translateX(-50%); } }
    @keyframes panelIn { to { opacity:1; transform:translateY(0); } }

    @media (max-width: 980px) {
      .nav-links { display: none; }
      .hero-grid { grid-template-columns: 1fr; gap: 40px; }
      .cards, .roadmap { grid-template-columns: 1fr 1fr; }
      .tab-panel { grid-template-columns: 1fr; }
    }
    @media (max-width: 680px) {
      .container { width: min(100% - 24px, 1180px); }
      .cards, .roadmap, .feature-list { grid-template-columns: 1fr; }
      .section-head { flex-direction: column; align-items: start; }
      .footer-inner { flex-direction: column; }
    }
  </style>
</head>
<body>
  <div class="noise"></div>
  <div class="orb one"></div>
  <div class="orb two"></div>

  <div class="nav-wrap">
    <nav class="nav">
      <a class="brand" href="#top"><span class="brand-mark">T</span><span class="brand-copy">TRUE ADAM<small>LOOKSMAXXING SYSTEM</small></span></a>
      <div class="nav-links">
        <a href="#scanner">ИИ-Сканер</a>
        <a href="#pillars">Направления</a>
        <a href="#system">Система</a>
        <a href="#roadmap">План</a>
        <a href="#faq">FAQ</a>
      </div>
      <a class="nav-cta" href="https://t.me/TrueAdam_Robot" target="_blank" rel="noopener">@TrueAdam_Robot</a>
    </nav>
  </div>

  <main id="top">
    <!-- HERO SECTION WITH INTEGRATED SCANNER -->
    <section class="hero">
      <div class="container hero-grid">
        <div class="hero-copy reveal">
          <div class="eyebrow"><span class="dot"></span> TRUE ADAM • NEXT LEVEL SYSTEM</div>
          <h1>Прокачай свою <span class="gradient-text">лучшую версию.</span></h1>
          <p>Системный ИИ-анализ внешности: сканирование Золотого Сечения, пропорций лица и персональный план трансформации прямо в Telegram.</p>
          <div class="hero-actions">
            <a class="primary" href="https://t.me/TrueAdam_Robot" target="_blank" rel="noopener">➤ Открыть @TrueAdam_Robot</a>
            <a class="secondary" href="#scanner">Запустить сканер лица</a>
          </div>
          <div class="micro">
            <span>Точный векторный анализ ДНК</span>
            <span>Без токсичных стандартов</span>
            <span>Только факты и уход</span>
          </div>
        </div>

        <!-- INTEGRATED SCANNER WIDGET -->
        <div class="scanner-widget-card reveal" id="scanner">
          <div style="font-family:'Orbitron',sans-serif; font-size:1.1rem; font-weight:800; color:var(--cyan); margin-bottom:6px;">ANIMUS MATRIX 5.0</div>
          <div style="font-size:0.8rem; color:var(--muted); margin-bottom:14px; text-transform:uppercase;">Векторный биометрический анализ</div>

          {% if not data %}
          <div class="gender-selector">
            <button class="gender-btn active" id="btnMale" onclick="selectGender('male')">🚹 МУЖЧИНА</button>
            <button class="gender-btn" id="btnFemale" onclick="selectGender('female')">🚺 ЖЕНЩИНА</button>
          </div>

          <div class="scan-status-bar" id="status-text">Анализ лица, сопоставление пропорций</div>

          <div id="scanner-wrap" onclick="document.getElementById('file-input').click()">
            <div class="placeholder-text" id="placeholder">
              [ ОЖИДАНИЕ ИЗОБРАЖЕНИЯ ]<br><br>
              Нажмите или перетащите фото сюда
            </div>
            <img id="user-image" alt="Target Face" crossorigin="anonymous">
            <canvas id="overlay-canvas"></canvas>
            <div class="laser-line" id="laser"></div>
          </div>

          <button class="btn-blood" onclick="document.getElementById('file-input').click()">Загрузить фото</button>
          <input type="file" id="file-input" accept="image/*">
          {% endif %}

          <div class="result-screen" id="resultScreen" style="{% if data %}display:flex;{% endif %}">
            <div id="scanner-wrap-res" style="height:260px; width:100%; border:1px solid var(--line); border-radius:14px; overflow:hidden; background:#000;">
              <img src="{% if data %}/static/uploads/{{ data.image_filename }}{% endif %}" style="width:100%; height:100%; object-fit:contain;" alt="Scan">
            </div>

            <div class="gauge-box">
              <svg viewBox="0 0 200 200">
                <circle class="gauge-bg-track" cx="100" cy="100" r="90"></circle>
                <circle class="gauge-fill-bar" id="gaugeBar" cx="100" cy="100" r="90"></circle>
              </svg>
              <div class="gauge-center">
                <div class="score-num" id="scoreNum">{% if data %}{{ "%.1f"|format(data.rating) }}{% else %}0.0{% endif %}</div>
              </div>
            </div>

            <div class="category-badge">{% if data %}{{ data.category }}{% endif %}</div>

            {% if data %}
            <div class="metrics-card">
              <div class="metric-row">
                <div class="metric-info"><span>👁 Глаза</span><span>{{ data.details.eyes }}/10.0</span></div>
                <div class="track-bar"><div class="fill-bar" style="width: {{ data.details.eyes * 10 }}%;"></div></div>
              </div>
              <div class="metric-row">
                <div class="metric-info"><span>🦴 Скулы</span><span>{{ data.details.cheekbones }}/10.0</span></div>
                <div class="track-bar"><div class="fill-bar" style="width: {{ data.details.cheekbones * 10 }}%;"></div></div>
              </div>
              <div class="metric-row">
                <div class="metric-info"><span>📐 Челюсть</span><span>{{ data.details.jaw }}/10.0</span></div>
                <div class="track-bar"><div class="fill-bar" style="width: {{ data.details.jaw * 10 }}%;"></div></div>
              </div>
              <div class="metric-row">
                <div class="metric-info"><span>💇‍♂️ Волосы</span><span>{{ data.details.hair }}/10.0</span></div>
                <div class="track-bar"><div class="fill-bar" style="width: {{ data.details.hair * 10 }}%;"></div></div>
              </div>
              <div class="metric-row">
                <div class="metric-info"><span>🧴 Кожа</span><span>{{ data.details.skin }}/10.0</span></div>
                <div class="track-bar"><div class="fill-bar" style="width: {{ data.details.skin * 10 }}%;"></div></div>
              </div>
              <div class="metric-row">
                <div class="metric-info">
                  <span>⚡ {% if data.gender == 'female' %}Женственность{% else %}Мужественность{% endif %}</span>
                  <span>{{ data.details.gender_feat }}/10.0</span>
                </div>
                <div class="track-bar"><div class="fill-bar" style="width: {{ data.details.gender_feat * 10 }}%;"></div></div>
              </div>
            </div>

            <div class="report-box">
              <div class="report-card"><div class="report-title" style="color:var(--gold);">💎 Потенциал</div><div>{{ data.report.potential }}</div></div>
              <div class="report-card"><div class="report-title" style="color:var(--success);">🔥 Плюсы</div><div>{{ data.report.pros }}</div></div>
              <div class="report-card"><div class="report-title" style="color:var(--pink);">❌ Недостатки</div><div>{{ data.report.cons }}</div></div>
              <div class="report-card"><div class="report-title" style="color:var(--cyan);">💡 Рекомендации</div><div>{{ data.report.recs }}</div></div>
            </div>
            {% endif %}

            <button class="btn-blood" onclick="location.href='/'">🔄 Новый сеанс</button>
          </div>

          <div class="watermark-footer">@TrueAdam_robot</div>
        </div>
      </div>
    </section>

    <!-- MARQUEE RIBBON -->
    <div class="marquee" aria-hidden="true">
      <div class="marquee-track">
        <span><i>✦</i> FACE</span><span><i>✦</i> BODY</span><span><i>✦</i> STYLE</span><span><i>✦</i> ENERGY</span><span><i>✦</i> DISCIPLINE</span><span><i>✦</i> @TrueAdam_Robot</span>
        <span><i>✦</i> FACE</span><span><i>✦</i> BODY</span><span><i>✦</i> STYLE</span><span><i>✦</i> ENERGY</span><span><i>✦</i> DISCIPLINE</span><span><i>✦</i> @TrueAdam_Robot</span>
      </div>
    </div>

    <!-- PILLARS SECTION -->
    <section id="pillars">
      <div class="container">
        <div class="section-head reveal">
          <div><span class="eyebrow">5 направлений</span><h2>Не маска. <br>Система.</h2></div>
          <p>Лучший результат появляется, когда внешность поддерживается здоровьем, привычками и личным стилем.</p>
        </div>

        <div class="tabs-shell reveal">
          <div class="tabs">
            <button class="tab-btn active" data-tab="face">Лицо и уход</button>
            <button class="tab-btn" data-tab="body">Тело</button>
            <button class="tab-btn" data-tab="style">Стиль</button>
            <button class="tab-btn" data-tab="energy">Энергия</button>
          </div>

          <div class="tab-panels">
            <div class="tab-panel active" id="face">
              <div class="feature-main">
                <div><div class="feature-icon">✦</div><h3>База ухода</h3><p>Очищение, увлажнение, SPF и аккуратный груминг. Минимум продуктов, максимум регулярности.</p></div>
                <div class="metric"><strong>4 шага</strong><span>утром и вечером</span></div>
              </div>
              <div class="feature-list">
                <div><h4>Кожа</h4><p>Мягкий уход, защита от солнца и постепенное внедрение активов.</p></div>
                <div><h4>Волосы</h4><p>Форма, подходящая чертам лица, и здоровая кожа головы.</p></div>
                <div><h4>Улыбка</h4><p>Гигиена, регулярные осмотры и натуральный ухоженный вид.</p></div>
                <div><h4>Груминг</h4><p>Брови, борода, ногти и аккуратные детали, которые собирают образ.</p></div>
              </div>
            </div>

            <div class="tab-panel" id="body">
              <div class="feature-main">
                <div><div class="feature-icon">◌</div><h3>Форма и осанка</h3><p>Силовые тренировки, мобильность и питание без жестких ограничений.</p></div>
                <div class="metric"><strong>3×</strong><span>тренировки в неделю</span></div>
              </div>
              <div class="feature-list">
                <div><h4>Сила</h4><p>Базовые упражнения и постепенный прогресс.</p></div>
                <div><h4>Осанка</h4><p>Сильная спина, мобильность и привычка держаться уверенно.</p></div>
                <div><h4>Питание</h4><p>Белок, овощи, вода и нормальный режим без крайностей.</p></div>
                <div><h4>Восстановление</h4><p>Сон и дни отдыха — часть прогресса, а не пауза.</p></div>
              </div>
            </div>

            <div class="tab-panel" id="style">
              <div class="feature-main">
                <div><div class="feature-icon">◇</div><h3>Личный код стиля</h3><p>Одежда должна усиливать человека, а не перекрывать его. Посадка важнее логотипа.</p></div>
                <div class="metric"><strong>80 / 20</strong><span>база и акценты</span></div>
              </div>
              <div class="feature-list">
                <div><h4>Силуэт</h4><p>Правильные пропорции делают образ собраннее.</p></div>
                <div><h4>Цвет</h4><p>Небольшая палитра помогает легко сочетать вещи.</p></div>
                <div><h4>Детали</h4><p>Обувь, аксессуары и фактуры создают характер.</p></div>
                <div><h4>Аутентичность</h4><p>Лучший стиль узнаваем, но не выглядит костюмом.</p></div>
              </div>
            </div>

            <div class="tab-panel" id="energy">
              <div class="feature-main">
                <div><div class="feature-icon">⌁</div><h3>Энергия и присутствие</h3><p>Выражение лица, голос, походка и спокойная уверенность часто заметнее идеальных черт.</p></div>
                <div class="metric"><strong>7–9 ч</strong><span>здорового сна</span></div>
              </div>
              <div class="feature-list">
                <div><h4>Сон</h4><p>Основа состояния кожи, аппетита и восстановления.</p></div>
                <div><h4>Стресс</h4><p>Прогулки, дыхание и цифровые паузы возвращают фокус.</p></div>
                <div><h4>Коммуникация</h4><p>Спокойный темп речи и зрительный контакт усиливают образ.</p></div>
                <div><h4>Уверенность</h4><p>Она растет из выполненных обещаний самому себе.</p></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- SYSTEM GRID -->
    <section id="system">
      <div class="container">
        <div class="section-head reveal">
          <div><span class="eyebrow">core system</span><h2>Маленькие детали. <br>Большой эффект.</h2></div>
          <p>Не нужно менять всё сразу. Выбери несколько рычагов, которые реально можно удерживать месяцами.</p>
        </div>

        <div class="cards">
          <article class="card reveal"><span class="card-number">01 / SKIN</span><h3>Чистая база</h3><p>Регулярный уход, SPF и терпение дают больше, чем хаотичная полка из десятков средств.</p></article>
          <article class="card reveal"><span class="card-number">02 / BODY</span><h3>Сильный силуэт</h3><p>Осанка, плечи, спина и общий тонус визуально меняют впечатление от человека.</p></article>
          <article class="card reveal"><span class="card-number">03 / STYLE</span><h3>Точная посадка</h3><p>Хорошо сидящая одежда почти всегда выглядит дороже и увереннее.</p></article>
          <article class="card reveal"><span class="card-number">04 / HAIR</span><h3>Правильная форма</h3><p>Стрижка с учетом структуры волос и формы лица задает характер всему образу.</p></article>
          <article class="card reveal"><span class="card-number">05 / SLEEP</span><h3>Восстановление</h3><p>Качественный сон поддерживает внешний вид, настроение и дисциплину.</p></article>
          <article class="card reveal"><span class="card-number">06 / MINDSET</span><h3>Спокойная уверенность</h3><p>Цель — не стать копией чужого идеала, а выглядеть ухоженно и чувствовать себя сильнее.</p></article>
        </div>
      </div>
    </section>

    <!-- ROADMAP SECTION -->
    <section id="roadmap">
      <div class="container">
        <div class="section-head reveal">
          <div><span class="eyebrow">30-day roadmap</span><h2>План без перегруза.</h2></div>
          <p>Простая последовательность, чтобы не сгореть на второй неделе.</p>
        </div>
        <div class="roadmap">
          <div class="step reveal"><span>01</span><h3>Аудит</h3><p>Фото, гардероб, сон, уход и физическая активность. Без самокритики — только факты.</p></div>
          <div class="step reveal"><span>02</span><h3>База</h3><p>Сон, вода, гигиена, простой уход и аккуратный внешний вид.</p></div>
          <div class="step reveal"><span>03</span><h3>Система</h3><p>Тренировки, стрижка, стиль и новые привычки по одной за раз.</p></div>
          <div class="step reveal"><span>04</span><h3>Калибровка</h3><p>Оставить работающие действия и убрать всё, что не даёт результата.</p></div>
        </div>
      </div>
    </section>

    <!-- MANIFESTO -->
    <section>
      <div class="container">
        <div class="manifesto reveal">
          <h2>Не гонись за идеалом.<br><span class="gradient-text">Создай свою форму.</span></h2>
          <p>Настоящий looksmaxxing — это уважение к себе, а не война с отражением. Улучшай то, что можешь контролировать, и не позволяй внешности определять твою ценность.</p>
        </div>
      </div>
    </section>

    <!-- FAQ SECTION -->
    <section id="faq">
      <div class="container">
        <div class="section-head reveal">
          <div><span class="eyebrow">questions</span><h2>FAQ</h2></div>
          <p>Коротко о безопасном и устойчивом подходе.</p>
        </div>
        <div class="faq">
          <div class="faq-item reveal"><button class="faq-q"><span>Что такое TRUE ADAM Looksmaxxing?</span><span>+</span></button><div class="faq-a">Это системное улучшение ухода, стиля, физической формы и общего впечатления. Здоровый подход не включает опасные эксперименты и навязчивое сравнение себя с другими.</div></div>
          <div class="faq-item reveal"><button class="faq-q"><span>С чего лучше начать?</span><span>+</span></button><div class="faq-a">Со сканирования лица в нашем ИИ-боте, сна, гигиены, базового ухода, стрижки и одежды правильного размера.</div></div>
          <div class="faq-item reveal"><button class="faq-q"><span>Нужны ли дорогие средства?</span><span>+</span></button><div class="faq-a">Нет. Регулярность, подходящие продукты и бережное отношение обычно важнее бренда и цены.</div></div>
        </div>
      </div>
    </section>
  </main>

  <footer>
    <div class="container footer-inner">
      <div><span style="font-weight:800; color:#fff;">TRUE ADAM</span> © 2026</div>
      <div>Looksmaxxing system • Telegram: <a style="color:var(--cyan);" href="https://t.me/TrueAdam_Robot" target="_blank" rel="noopener">@TrueAdam_Robot</a></div>
    </div>
  </footer>

  <a class="floating-telegram" href="https://t.me/TrueAdam_Robot" target="_blank" rel="noopener"><span>➤</span><span>@TrueAdam_Robot</span></a>

  <script>
    let selectedGender = 'male';
    function selectGender(g) {
      selectedGender = g;
      document.getElementById('btnMale').classList.toggle('active', g === 'male');
      document.getElementById('btnFemale').classList.toggle('active', g === 'female');
    }

    let tgUser = { id: 0, name: 'Объект Анимуса', username: '' };
    if (window.Telegram && window.Telegram.WebApp) {
      window.Telegram.WebApp.ready();
      if (window.Telegram.WebApp.initDataUnsafe && window.Telegram.WebApp.initDataUnsafe.user) {
        const u = window.Telegram.WebApp.initDataUnsafe.user;
        tgUser.id = u.id || 0;
        tgUser.name = (u.first_name || '') + ' ' + (u.last_name || '');
        tgUser.username = u.username || '';
      }
    }

    const fileInput = document.getElementById('file-input');
    const userImage = document.getElementById('user-image');
    const placeholder = document.getElementById('placeholder');
    const laser = document.getElementById('laser');
    const canvas = document.getElementById('overlay-canvas');
    const ctx = canvas ? canvas.getContext('2d') : null;
    const statusText = document.getElementById('status-text');

    let faceMesh;
    let currentLandmarks = null;

    function initFaceMesh() {
      if (typeof FaceMesh === 'undefined') return;
      faceMesh = new FaceMesh({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`
      });

      faceMesh.setOptions({
        maxNumFaces: 1,
        refineLandmarks: true,
        minDetectionConfidence: 0.1,
        minTrackingConfidence: 0.1
      });

      faceMesh.onResults((results) => {
        if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {
          currentLandmarks = results.multiFaceLandmarks[0];
        } else {
          currentLandmarks = null;
        }
      });
    }

    if (fileInput) {
      fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
          userImage.src = event.target.result;
          userImage.style.display = 'block';
          placeholder.style.display = 'none';

          userImage.onload = async () => {
            alignCanvasToImage();
            if (faceMesh) {
              await faceMesh.send({ image: userImage });
            }
            startScanProcess(file);
          };
        };
        reader.readAsDataURL(file);
      });
    }

    function alignCanvasToImage() {
      if (!canvas || !userImage) return;
      canvas.width = userImage.clientWidth;
      canvas.height = userImage.clientHeight;
      canvas.style.top = userImage.offsetTop + 'px';
      canvas.style.left = userImage.offsetLeft + 'px';
      canvas.style.width = userImage.clientWidth + 'px';
      canvas.style.height = userImage.clientHeight + 'px';
    }

    async function startScanProcess(file) {
      laser.classList.add('laser-active');
      canvas.style.opacity = 0;
      statusText.innerText = 'Анализ лица, сопоставление пропорций...';

      await new Promise(r => setTimeout(r, 1200));

      if (currentLandmarks) {
        drawPreciseBlueMesh(currentLandmarks);
      }

      canvas.style.opacity = 1;
      document.getElementById('scanner-wrap').classList.add('success-flash');

      const formData = new FormData();
      formData.append('file', file);
      formData.append('gender', selectedGender);
      formData.append('user_id', tgUser.id);
      formData.append('user_name', tgUser.name);
      formData.append('user_username', tgUser.username);

      try {
        const response = await fetch('/analyze', { method: 'POST', body: formData });
        const data = await response.json();
        if (data.id) window.location.href = '/result/' + data.id;
      } catch (err) {
        location.reload();
      }
    }

    function drawPreciseBlueMesh(landmarks) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const w = canvas.width;
      const h = canvas.height;

      ctx.strokeStyle = '#6cf5ff';
      ctx.fillStyle = '#6cf5ff';
      ctx.lineWidth = 1;

      if (typeof FACEMESH_TESSELATION !== 'undefined') {
        ctx.beginPath();
        for (let i = 0; i < FACEMESH_TESSELATION.length; i++) {
          const p1 = landmarks[FACEMESH_TESSELATION[i][0]];
          const p2 = landmarks[FACEMESH_TESSELATION[i][1]];
          ctx.moveTo(p1.x * w, p1.y * h);
          ctx.lineTo(p2.x * w, p2.y * h);
        }
        ctx.stroke();
      }

      for (let i = 0; i < landmarks.length; i += 5) {
        const x = landmarks[i].x * w;
        const y = landmarks[i].y * h;
        ctx.beginPath();
        ctx.arc(x, y, 1.2, 0, 2 * Math.PI);
        ctx.fill();
      }
    }

    window.addEventListener('load', initFaceMesh);

    {% if data %}
    const rating = {{ data.rating }};
    const gaugeBar = document.getElementById('gaugeBar');
    const scoreNum = document.getElementById('scoreNum');

    gaugeBar.style.stroke = "{{ data.color_hex }}";
    const offset = (2 * Math.PI * 90) - (rating / 10.0) * (2 * Math.PI * 90);

    setTimeout(() => {
      gaugeBar.style.strokeDashoffset = offset;
    }, 150);

    let cur = 0.0;
    const step = rating / 40.0;
    const t = setInterval(() => {
      cur += step;
      if (cur >= rating) {
        scoreNum.innerText = rating.toFixed(1);
        clearInterval(t);
      } else {
        scoreNum.innerText = cur.toFixed(1);
      }
    }, 30);
    {% endif %}

    // TAB CONTROLS & INTERACTION
    const tabButtons = document.querySelectorAll('.tab-btn');
    const panels = document.querySelectorAll('.tab-panel');

    tabButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        tabButtons.forEach(b => b.classList.remove('active'));
        panels.forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        const panel = document.getElementById(btn.dataset.tab);
        if (panel) panel.classList.add('active');
      });
    });

    // FAQ ACCORDION
    document.querySelectorAll('.faq-q').forEach(button => {
      button.addEventListener('click', () => {
        const item = button.parentElement;
        document.querySelectorAll('.faq-item').forEach(el => {
          if (el !== item) el.classList.remove('open');
        });
        item.classList.toggle('open');
      });
    });

    // REVEAL ANIMATIONS
    const revealObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          revealObserver.unobserve(entry.target);
        }
      });
    }, { threshold: .1 });
    document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));
  </script>
</body>
</html>
"""

# ==============================================================================
# 🛰 ROUTES (FLASK + ADMIN PHOTO FORWARDING)
# ==============================================================================
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, data=None)

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']

    gender = request.form.get('gender', 'male')
    user_id_str = request.form.get('user_id', '0')
    user_id = int(user_id_str) if user_id_str.isdigit() else 0
    user_name = request.form.get('user_name', 'Объект Анимуса')
    user_username = request.form.get('user_username', '')

    unique_id = f"{uuid.uuid4().hex}_{int(time.time())}"
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{unique_id}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    archive_path = os.path.join(PHOTOS_DIR, f"web_user_{user_id}_{filename}")
    cv2.imwrite(archive_path, cv2.imread(filepath))

    rating, category, cat_class, color_hex, details, report = analyze_opencv(filepath, gender)

    results_db[unique_id] = {
        "rating": rating,
        "category": category,
        "cat_class": cat_class,
        "color_hex": color_hex,
        "details": details,
        "report": report,
        "gender": gender,
        "image_filename": filename
    }

    def save_db_async():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        if user_id != 0:
            loop.run_until_complete(db.register_user(user_id, user_username, user_name))
        loop.run_until_complete(db.add_scan(unique_id, user_id, rating, category, gender, archive_path, source="web"))

    threading.Thread(target=save_db_async, daemon=True).start()

    logger.info(f"[LOG OWNER] Новый запуск на сайте: Name='{user_name}', Username='@{user_username}', UserID={user_id}, Rating={rating}")

    if ADMIN_ID and ADMIN_ID != 0 and user_id != ADMIN_ID:
        def send_admin_photo_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                async def _send():
                    bot_admin = Bot(token=BOT_TOKEN)
                    admin_caption = (
                        f"⚔️ **НОВАЯ ИНИЦИАЦИЯ В АНИМУС (САЙТ)!**\n\n"
                        f"👤 **Имя:** {user_name}\n"
                        f"🏷 **Юзернейм:** @{user_username if user_username else 'отсутствует'}\n"
                        f"🆔 **ID:** `{user_id}`\n"
                        f"📊 **Рейтинг ДНК:** `{rating}/10` ({category})\n\n"
                        f"🏷 `@TrueAdam_robot`"
                    )
                    photo_file = FSInputFile(filepath)
                    await bot_admin.send_photo(chat_id=ADMIN_ID, photo=photo_file, caption=admin_caption, parse_mode="Markdown")
                    await bot_admin.session.close()
                loop.run_until_complete(_send())
            except Exception as e:
                logger.error(f"Ошибка отправки фото админу с сайта: {e}")

        threading.Thread(target=send_admin_photo_async, daemon=True).start()

    return jsonify({"rating": rating, "category": category, "id": unique_id})

@app.route('/result/<result_id>')
def show_result(result_id):
    data = results_db.get(result_id)
    return render_template_string(HTML_TEMPLATE, data=data)

threading.Thread(target=start_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
