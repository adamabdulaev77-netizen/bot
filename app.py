# ==============================================================================
# 🌐 AESTHETIC VISION AI — ANIMUS MATRIX ULTIMATE EDITION (GROQ + VOICE + GENDER)
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
# gTTS>=2.5.0
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

from flask import Flask, request, jsonify, render_template_string, send_from_directory

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
    from gtts import gTTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

# ==============================================================================
# ⚙️ ГЛОБАЛЬНАЯ КОНФИГУРАЦИЯ СИСТЕМЫ
# ==============================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8483343132:AAErzKkD_F0f2Fd3DHRyf0pi1SqT9ZYv5Tk")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1175620687"))

# Ключ Groq API
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
logger = logging.getLogger("AnimusMatrixEnterprise")

app = Flask(__name__, static_folder='static')
results_db: Dict[str, Dict[str, Any]] = {}

# Состояния FSM для выбора пола перед сканированием
class ScanStates(StatesGroup):
    waiting_for_gender = State()
    waiting_for_photo = State()

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
# 🎙 СИНТЕЗ ГОЛОСОВЫХ СООБЩЕНИЙ (TTS ENGINE)
# ==============================================================================
def create_voice_note(text: str) -> Optional[str]:
    """Генерация голосового файла mp3"""
    if not TTS_AVAILABLE:
        return None
    try:
        clean_text = text.replace('*', '').replace('_', '').replace('`', '').replace('#', '')
        if len(clean_text) > 450:
            clean_text = clean_text[:450] + "..."
        
        filename = f"voice_{uuid.uuid4().hex[:8]}.mp3"
        filepath = os.path.join(VOICE_DIR, filename)
        
        tts = gTTS(text=clean_text, lang='ru', slow=False)
        tts.save(filepath)
        return filepath
    except Exception as e:
        logger.error(f"Ошибка создания голосового сообщения: {e}")
        return None

# ==============================================================================
# 🧠 GROQ AI ДВИЖОК (ГЛУБОКИЙ АНАЛИЗ И ЧАТ)
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

    models = ["llama-3.3-70b-versatile", "llama3-70b-8192", "mixtral-8x7b-32768"]

    for model_name in models:
        data = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7
        }
        try:
            r = requests.post(GROQ_API_URL, json=data, headers=headers, timeout=12)
            if r.status_code == 200:
                res_json = r.json()
                return res_json["choices"][0]["message"]["content"].strip()
            else:
                logger.warning(f"Groq model {model_name} status [{r.status_code}]: {r.text[:150]}")
        except Exception as e:
            logger.error(f"Ошибка вызова Groq model {model_name}: {e}")

    return "⚠️ Произошла ошибка связи с нейросетью."

def analyze_with_groq_deep(sym_pct: float, sharp_score: float, harm_score: float, gender: str = "male"):
    gender_title = "МУЖЧИНА" if gender == "male" else "ЖЕНЩИНА"
    
    system_prompt = (
        f"Ты — главный ИИ-эксперт сервиса Animus Matrix по биометрическому разбору лиц, Золотому Сечению и луксмаксингу. "
        f"Объект анализа: {gender_title}.\n"
        "Оценивай внешность строго, беспристрастно по шкале от 1.0 до 10.0.\n"
        f"{'Акцент при анализе мужчины: угол челюсти, ширина подбородка, кантальный тильт, маскулинная резкость и пропорция третей.' if gender == 'male' else 'Акцент при анализе женщины: мягкость овала, пропорции губ и скул, гладкость кожи, симметрия глаз и эстетический баланс.'}\n\n"
        "Верни ответ СТРОГО в формате JSON без markdown разметки:\n"
        '{\n'
        '  "rating": 7.2,\n'
        '  "category": "HTN",\n'
        '  "pros": "1. Высокая симметрия овала лица (88%).\\n2. Четко выраженная дуга челюсти.\\n3. Отличный цветовой баланс и контраст кадра.",\n'
        '  "cons": "1. Легкая асимметрия в области подбородка.\\n2. Сглаженная резкость в средней третьей части лица.\\n3. Небольшие отеки под глазами.",\n'
        '  "recs": "1. ДЕФАТТИНГ: Снизь процент жира в организме до 11-13% для максимального рельефа скул.\\n2. МЬЮИНГ И ОСАНКА: Сохраняй правильное положение языка у нёба и держи плечевой пояс.\\n3. УХОД ЗА КОЖЕЙ: Включи гиалуроновую кислоту и салициловый тоник от микроотеков.\\n4. ПРИЧЕСКА: Подбери объемную стрижку под форму овала.",\n'
        '  "potential": "8.7 (CHAD)"\n'
        '}'
    )

    prompt = f"Векторные данные кадра: Симметрия овала={sym_pct}%, Индекс контурной четкости={sharp_score}/10, Цветовой тон={harm_score}/10. Пол={gender_title}."

    response_text = ask_groq_ai(prompt, system_prompt)
    try:
        if response_text.startswith("```json"): response_text = response_text[7:]
        if response_text.endswith("```"): response_text = response_text[:-3]
        ai_json = json.loads(response_text.strip())
        return (
            float(ai_json.get("rating", 6.0)),
            str(ai_json.get("category", "MTN")),
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

    return rating, cat, pros, cons, recs, pot

def analyze_opencv(image_path: str, gender: str = "male"):
    img = cv2.imread(image_path)
    if img is None:
        return 5.0, "LTN", "cat-LTN", "#ffffff", {"symmetry": 50.0, "sharpness": 5.0, "harmony": 5.0}, {
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

    rating, cat, pros, cons, recs, potential = analyze_with_groq_deep(sym_pct, sharp_score, harm_score, gender)

    if rating < 3.0: cat_cls, color = "cat-SUB3", "#ff3333"
    elif rating < 5.0: cat_cls, color = "cat-SUB5", "#ff8833"
    elif rating < 6.0: cat_cls, color = "cat-LTN", "#e6e6e6"
    elif rating < 7.0: cat_cls, color = "cat-MTN", "#cccccc"
    elif rating < 8.0: cat_cls, color = "cat-HTN", "#ffffff"
    elif rating < 10.0: cat_cls, color = "cat-CHAD", "#00e5ff"
    else: cat_cls, color = "cat-TRUE_ADAM", "#ffd700"

    details = {"symmetry": sym_pct, "sharpness": sharp_score, "harmony": harm_score}
    report = {"pros": pros, "cons": cons, "recs": recs, "potential": potential}

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
    share_text = f"🔥 Мой генетический индекс внешности в Animus Matrix: {rating}/10 ({category})! Проверь себя:"
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
        "🔥 Я — ИИ-агент по векторному анализу привлекательности, пропорций и геометрии лица.\n\n"
        "📸 **Нажми «📸 Проверить лицо»** или **задай любой вопрос** прямо в чат! 👇"
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

@router.message(F.text == "📊 Мой профиль")
async def btn_profile(message: Message):
    stats = await db.get_user_stats(message.from_user.id)
    profile_text = (
        f"👤 **Профиль:** {message.from_user.first_name}\n"
        f"🆔 **ID:** `{message.from_user.id}`\n\n"
        f"📈 **Проверок сделано:** {stats['scans']}\n"
        f"💬 **Вопросов ИИ:** {stats['chats']}\n"
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

        # Отправка копии снимка админу
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

        detailed_text = (
            f"✅ **ПОЛНОЦЕННЫЙ БИОМЕТРИЧЕСКИЙ РАЗБОР:**\n\n"
            f"📊 **Твой рейтинг:** `{rating} / 10` ({category})\n"
            f"💎 **Потенциал:** `{report.get('potential', '8.5 CHAD')}`\n\n"
            f"🔥 **ГЕНЕТИЧЕСКИЕ ПЛЮСЫ:**\n{report['pros']}\n\n"
            f"❌ **ЗОНЫ ДЕСИНХРОНИЗАЦИИ:**\n{report['cons']}\n\n"
            f"💡 **ПОШАГОВЫЙ ПЛАН ПРОКАЧКИ:**\n{report['recs']}"
        )

        await status_msg.edit_text(
            detailed_text,
            parse_mode="Markdown",
            reply_markup=get_result_inline_keyboard(scan_id, rating, category)
        )

        # Озвучка разбора
        summary_voice_text = f"Ваш рейтинг {rating} из 10. Категория {category}. Потенциал {report.get('potential', 'высокий')}. Подробный план смотрите в карточке."
        voice_file = create_voice_note(summary_voice_text)
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

# 💬 ОБРАБОТЧИК ЧАТА С ИИ-АГЕНТОМ (ТЕКСТ + ГОЛОС)
@router.message(F.text & ~F.text.startswith("/"))
async def handle_ai_chat_message(message: Message):
    if message.text in ["📸 Проверить лицо", "📊 Мой профиль", "🏆 Таблица категорий", "👨‍💻 Админ-панель"]:
        return

    status_msg = await message.answer("💬 *ИИ-агент обдумывает ответ...*", parse_mode="Markdown")
    
    loop = asyncio.get_event_loop()
    sys_prompt = "Ты — ИИ-агент сервиса Animus Matrix. Эксперт по луксмаксингу, спорту, стилю и уходу. Отвечай прямо, четко, содержательно."
    ai_reply = await loop.run_in_executor(None, ask_groq_ai, message.text, sys_prompt)
    
    await status_msg.edit_text(ai_reply, parse_mode="Markdown")
    await db.add_chat_log(message.from_user.id, message.text, ai_reply)

    # Генерация голосового сообщения в ответ
    voice_file = create_voice_note(ai_reply)
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
# 🎨 ASSASSIN'S CREED ANIMUS MATRIX FRONTEND TEMPLATE
# ==============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ANIMUS 3.0 — Memory Corridor Synchronization</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800;900&family=Rajdhani:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --animus-white: #ffffff;
            --animus-silver: #e0e6ed;
            --animus-gray: rgba(255, 255, 255, 0.15);
            --animus-glow: rgba(255, 255, 255, 0.85);
            --animus-cyan: #00f0ff;
            --animus-card: rgba(12, 16, 24, 0.82);
            --animus-border: rgba(255, 255, 255, 0.25);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Rajdhani', sans-serif;
            user-select: none;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            background: #05070a;
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow-x: hidden;
            position: relative;
            padding: 20px 12px;
        }

        #animus-canvas, #confetti-canvas {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
        }
        #animus-canvas { z-index: 0; }
        #confetti-canvas { z-index: 100; }

        .scanline-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%),
                        linear-gradient(90deg, rgba(255, 0, 0, 0.03), rgba(0, 255, 0, 0.01), rgba(0, 0, 255, 0.03));
            background-size: 100% 3px, 6px 100%;
            pointer-events: none;
            z-index: 2;
        }

        .animus-card {
            position: relative;
            z-index: 10;
            width: 100%;
            max-width: 530px;
            background: var(--animus-card);
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border: 1px solid var(--animus-border);
            border-radius: 20px;
            padding: 32px 24px;
            box-shadow: 0 0 50px rgba(255, 255, 255, 0.12),
                        inset 0 0 20px rgba(255, 255, 255, 0.05);
            animation: animusAppear 1s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            clip-path: polygon(0 0, 95% 0, 100% 5%, 100% 100%, 5% 100%, 0 95%);
        }

        @keyframes animusAppear {
            from { opacity: 0; transform: scale(0.92) translateY(30px); }
            to { opacity: 1; transform: scale(1) translateY(0); }
        }

        .animus-corner {
            position: absolute;
            width: 16px;
            height: 16px;
            border: 2px solid #ffffff;
            pointer-events: none;
        }
        .top-left { top: 8px; left: 8px; border-right: none; border-bottom: none; }
        .bottom-right { bottom: 8px; right: 8px; border-left: none; border-top: none; }

        .header {
            text-align: center;
            margin-bottom: 24px;
            position: relative;
        }
        .header .badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 4px 16px;
            border-radius: 4px;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.3);
            font-family: 'Orbitron', sans-serif;
            font-size: 0.72rem;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 12px;
            box-shadow: 0 0 15px rgba(255, 255, 255, 0.2);
        }
        .header h1 {
            font-family: 'Orbitron', sans-serif;
            font-size: 2.1rem;
            font-weight: 900;
            letter-spacing: 2px;
            color: #ffffff;
            text-shadow: 0 0 20px rgba(255, 255, 255, 0.6);
            text-transform: uppercase;
        }
        .header p {
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.6);
            margin-top: 6px;
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        .gender-selector {
            display: flex;
            gap: 10px;
            margin-bottom: 18px;
            justify-content: center;
        }
        .gender-btn {
            flex: 1;
            padding: 10px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #ffffff;
            font-family: 'Orbitron', sans-serif;
            font-size: 0.8rem;
            font-weight: 700;
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.3s;
        }
        .gender-btn.active {
            background: #ffffff;
            color: #000000;
            box-shadow: 0 0 15px rgba(255, 255, 255, 0.6);
        }

        .upload-box {
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 12px;
            padding: 40px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.4s ease;
            background: rgba(255, 255, 255, 0.02);
            position: relative;
            overflow: hidden;
        }
        .upload-box:hover {
            border-color: #ffffff;
            background: rgba(255, 255, 255, 0.08);
            box-shadow: 0 0 30px rgba(255, 255, 255, 0.25);
        }
        .upload-icon {
            font-size: 2.8rem;
            margin-bottom: 12px;
            color: #ffffff;
            text-shadow: 0 0 15px #ffffff;
        }
        .upload-title {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.1rem;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }
        .upload-subtitle {
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.5);
            margin-top: 4px;
            margin-bottom: 22px;
        }
        .btn-animus {
            display: inline-block;
            background: #ffffff;
            color: #000000;
            padding: 14px 36px;
            font-family: 'Orbitron', sans-serif;
            font-weight: 900;
            font-size: 0.85rem;
            letter-spacing: 2px;
            text-transform: uppercase;
            border: none;
            clip-path: polygon(10% 0, 100% 0, 90% 100%, 0 100%);
            box-shadow: 0 0 20px rgba(255, 255, 255, 0.5);
            transition: all 0.3s ease;
        }
        .btn-animus:hover {
            background: var(--animus-cyan);
            box-shadow: 0 0 30px var(--animus-cyan);
        }
        #fileInput { display: none; }

        .loader-screen {
            display: none;
            text-align: center;
            padding: 40px 10px;
        }
        .laser-loader {
            width: 100%;
            height: 3px;
            background: rgba(255, 255, 255, 0.1);
            position: relative;
            overflow: hidden;
            margin-bottom: 20px;
        }
        .laser-line {
            position: absolute;
            top: 0;
            left: -50%;
            width: 50%;
            height: 100%;
            background: linear-gradient(90deg, transparent, #ffffff, transparent);
            animation: laserScan 1.2s infinite ease-in-out;
        }
        @keyframes laserScan {
            0% { left: -50%; }
            100% { left: 100%; }
        }
        .loader-text {
            font-family: 'Orbitron', sans-serif;
            font-size: 0.9rem;
            letter-spacing: 2px;
            color: #ffffff;
            text-transform: uppercase;
        }

        .result-screen {
            display: none;
            flex-direction: column;
            align-items: center;
            gap: 22px;
        }

        .photo-container {
            width: 100%;
            height: 330px;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.2);
            background: #000000;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            box-shadow: 0 0 30px rgba(0, 0, 0, 0.8);
        }
        .photo-container img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }

        .gauge-box {
            position: relative;
            width: 190px;
            height: 190px;
        }
        .gauge-box svg {
            width: 100%;
            height: 100%;
            transform: rotate(-90deg);
        }
        .gauge-bg-track {
            fill: none;
            stroke: rgba(255, 255, 255, 0.08);
            stroke-width: 12;
        }
        .gauge-fill-bar {
            fill: none;
            stroke-width: 12;
            stroke-linecap: square;
            stroke-dasharray: 565.48;
            stroke-dashoffset: 565.48;
            transition: stroke-dashoffset 2s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .gauge-center {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
        }
        .score-num {
            font-family: 'Orbitron', sans-serif;
            font-size: 3.5rem;
            font-weight: 900;
            line-height: 1;
            color: #ffffff;
            text-shadow: 0 0 15px rgba(255, 255, 255, 0.8);
        }
        .score-lbl {
            font-size: 0.8rem;
            color: rgba(255, 255, 255, 0.5);
            font-weight: 700;
            letter-spacing: 2px;
            text-transform: uppercase;
        }

        .category-badge {
            padding: 10px 32px;
            font-family: 'Orbitron', sans-serif;
            font-size: 1.35rem;
            font-weight: 900;
            letter-spacing: 3px;
            text-transform: uppercase;
            border: 1px solid rgba(255, 255, 255, 0.4);
            background: rgba(255, 255, 255, 0.05);
            box-shadow: 0 0 25px rgba(255, 255, 255, 0.2);
            clip-path: polygon(8% 0, 100% 0, 92% 100%, 0 100%);
        }

        .metrics-card {
            width: 100%;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 18px;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }
        .metric-row { display: flex; flex-direction: column; gap: 6px; }
        .metric-info { display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; }
        .metric-name { color: rgba(255, 255, 255, 0.6); }
        .metric-value { color: #ffffff; }
        .track-bar {
            height: 6px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 2px;
            overflow: hidden;
        }
        .fill-bar {
            height: 100%;
            width: 0%;
            background: #ffffff;
            box-shadow: 0 0 10px #ffffff;
            transition: width 1.6s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .report-box {
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .report-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 16px;
            text-align: left;
        }
        .report-title {
            font-family: 'Orbitron', sans-serif;
            font-size: 0.85rem;
            font-weight: 800;
            letter-spacing: 1.5px;
            margin-bottom: 6px;
            text-transform: uppercase;
        }
        .title-pros { color: #ffffff; }
        .title-cons { color: #ff5555; }
        .title-recs { color: var(--animus-cyan); }
        .title-pot { color: #ffd700; }
        .report-text {
            font-size: 0.88rem;
            color: rgba(255, 255, 255, 0.85);
            line-height: 1.5;
            white-space: pre-line;
        }

        .action-buttons {
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .btn-share {
            width: 100%;
            background: var(--animus-cyan);
            border: 1px solid var(--animus-cyan);
            color: #000000;
            padding: 14px;
            font-family: 'Orbitron', sans-serif;
            font-weight: 900;
            font-size: 0.85rem;
            letter-spacing: 2px;
            text-transform: uppercase;
            cursor: pointer;
            box-shadow: 0 0 15px var(--animus-cyan);
            transition: all 0.3s;
        }
        .btn-share:hover { opacity: 0.9; }

        .btn-reload {
            width: 100%;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.25);
            color: #ffffff;
            padding: 14px;
            font-family: 'Orbitron', sans-serif;
            font-weight: 800;
            font-size: 0.85rem;
            letter-spacing: 2px;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-reload:hover { background: #ffffff; color: #000000; }
    </style>
</head>
<body>
    <div class="scanline-overlay"></div>

    <canvas id="animus-canvas"></canvas>
    <canvas id="confetti-canvas"></canvas>

    <div class="animus-card">
        <div class="animus-corner top-left"></div>
        <div class="animus-corner bottom-right"></div>

        <div class="header">
            <div class="badge">⚔️ ABSTERGO ANIMUS 3.0</div>
            <h1>SYSTEM MATRIX</h1>
            <p>Синхронизация генетической памяти лица</p>
        </div>

        {% if not data %}
        <div class="gender-selector">
            <button class="gender-btn active" id="btnMale" onclick="selectGender('male')">🚹 МУЖЧИНА</button>
            <button class="gender-btn" id="btnFemale" onclick="selectGender('female')">🚺 ЖЕНЩИНА</button>
        </div>

        <div class="upload-box" id="uploadBox" onclick="document.getElementById('fileInput').click()">
            <div class="upload-icon">💠</div>
            <div class="upload-title">Загрузить объект</div>
            <div class="upload-subtitle">Выберите портретный файл для инициализации матрицы</div>
            <div class="btn-animus">Инициация</div>
            <input type="file" id="fileInput" accept="image/*" onchange="uploadPhoto(this)">
        </div>

        <div class="loader-screen" id="loaderScreen">
            <div class="laser-loader">
                <div class="laser-line"></div>
            </div>
            <div class="loader-text">Проводится глубокий векторный анализ ДНК...</div>
        </div>
        {% endif %}

        <div class="result-screen" id="resultScreen" style="{% if data %}display:flex;{% endif %}">
            <div class="photo-container">
                <img src="{% if data %}/static/uploads/{{ data.image_filename }}{% endif %}" alt="Animus Scan">
            </div>

            <div class="gauge-box">
                <svg viewBox="0 0 200 200">
                    <circle class="gauge-bg-track" cx="100" cy="100" r="90"></circle>
                    <circle class="gauge-fill-bar" id="gaugeBar" cx="100" cy="100" r="90"></circle>
                </svg>
                <div class="gauge-center">
                    <div class="score-num" id="scoreNum">{% if data %}{{ "%.1f"|format(data.rating) }}{% else %}0.0{% endif %}</div>
                    <div class="score-lbl">Индекс DNA</div>
                </div>
            </div>

            <div class="category-badge {% if data %}{{ data.cat_class }}{% endif %}">
                {% if data %}{{ data.category }}{% endif %}
            </div>

            {% if data %}
            <div class="metrics-card">
                <div class="metric-row">
                    <div class="metric-info">
                        <span class="metric-name">Симметрия овала</span>
                        <span class="metric-value">{{ data.details.symmetry }}%</span>
                    </div>
                    <div class="track-bar">
                        <div class="fill-bar" id="symBar"></div>
                    </div>
                </div>

                <div class="metric-row">
                    <div class="metric-info">
                        <span class="metric-name">Четкость геометрии</span>
                        <span class="metric-value">{{ data.details.sharpness }}/10.0</span>
                    </div>
                    <div class="track-bar">
                        <div class="fill-bar" id="sharpBar"></div>
                    </div>
                </div>

                <div class="metric-row">
                    <div class="metric-info">
                        <span class="metric-name">Спектральный тон</span>
                        <span class="metric-value">{{ data.details.harmony }}/10.0</span>
                    </div>
                    <div class="track-bar">
                        <div class="fill-bar" id="harmBar"></div>
                    </div>
                </div>
            </div>

            <div class="report-box">
                <div class="report-card">
                    <div class="report-title title-pot">💎 Максимальный потенциал</div>
                    <div class="report-text">{{ data.report.potential }}</div>
                </div>
                <div class="report-card">
                    <div class="report-title title-pros">🔥 Генетические плюсы анатомии</div>
                    <div class="report-text">{{ data.report.pros }}</div>
                </div>
                <div class="report-card">
                    <div class="report-title title-cons">❌ Дессинхронизация и недостатки</div>
                    <div class="report-text">{{ data.report.cons }}</div>
                </div>
                <div class="report-card">
                    <div class="report-title title-recs">💡 Пошаговая инструкция прокачки</div>
                    <div class="report-text">{{ data.report.recs }}</div>
                </div>
            </div>
            {% endif %}

            <div class="action-buttons">
                {% if data %}
                <button class="btn-share" onclick="shareResult()">📲 Поделиться результатом</button>
                {% endif %}
                <button class="btn-reload" onclick="location.href='/'">🔄 Новый сеанс Анимуса</button>
            </div>
        </div>
    </div>

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
            window.Telegram.WebApp.expand();
            if (window.Telegram.WebApp.initDataUnsafe && window.Telegram.WebApp.initDataUnsafe.user) {
                const u = window.Telegram.WebApp.initDataUnsafe.user;
                tgUser.id = u.id || 0;
                tgUser.name = (u.first_name || '') + ' ' + (u.last_name || '');
                tgUser.username = u.username || '';
            }
        }

        const canvas = document.getElementById('animus-canvas');
        const ctx = canvas.getContext('2d');

        function resize() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }
        window.addEventListener('resize', resize);
        resize();

        let animusLines = [];
        for (let i = 0; i < 35; i++) {
            animusLines.push({
                x: Math.random() * canvas.width,
                length: Math.random() * 200 + 80,
                speed: Math.random() * 4 + 1.5,
                width: Math.random() * 2 + 0.5,
                opacity: Math.random() * 0.4 + 0.1
            });
        }

        let memoryParticles = [];
        for (let i = 0; i < 60; i++) {
            memoryParticles.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                size: Math.random() * 3 + 1,
                vx: (Math.random() - 0.5) * 0.5,
                vy: -Math.random() * 1.5 - 0.5,
                alpha: Math.random() * 0.6 + 0.2
            });
        }

        let gridOffset = 0;

        function renderAnimusMatrix() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            gridOffset += 0.4;
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
            ctx.lineWidth = 1;

            const gridSize = 40;
            for (let x = 0; x < canvas.width; x += gridSize) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, canvas.height);
                ctx.stroke();
            }
            for (let y = (gridOffset % gridSize); y < canvas.height; y += gridSize) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(canvas.width, y);
                ctx.stroke();
            }

            animusLines.forEach(l => {
                l.x += l.speed;
                if (l.x > canvas.width + l.length) l.x = -l.length;

                ctx.strokeStyle = `rgba(255, 255, 255, ${l.opacity})`;
                ctx.lineWidth = l.width;
                ctx.shadowColor = '#ffffff';
                ctx.shadowBlur = 10;
                ctx.beginPath();
                ctx.moveTo(l.x - l.length, canvas.height / 2 + (l.width * 50));
                ctx.lineTo(l.x, canvas.height / 2 + (l.width * 50));
                ctx.stroke();
            });

            memoryParticles.forEach(p => {
                p.x += p.vx;
                p.y += p.vy;
                if (p.y < 0) p.y = canvas.height;
                if (p.x < 0) p.x = canvas.width;
                if (p.x > canvas.width) p.x = 0;

                ctx.fillStyle = `rgba(255, 255, 255, ${p.alpha})`;
                ctx.shadowColor = '#ffffff';
                ctx.shadowBlur = 6;
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                ctx.fill();
            });

            ctx.shadowBlur = 0;
            requestAnimationFrame(renderAnimusMatrix);
        }
        renderAnimusMatrix();

        function playAnimusSound() {
            try {
                const AudioCtx = window.AudioContext || window.webkitAudioContext;
                if (!AudioCtx) return;
                const actx = new AudioCtx();
                const osc = actx.createOscillator();
                const gain = actx.createGain();

                osc.type = 'sine';
                osc.frequency.setValueAtTime(120, actx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(440, actx.currentTime + 0.4);

                gain.gain.setValueAtTime(0.15, actx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, actx.currentTime + 0.4);

                osc.connect(gain);
                gain.connect(actx.destination);
                osc.start();
                osc.stop(actx.currentTime + 0.4);
            } catch (e) {}
        }

        async function uploadPhoto(input) {
            if (!input.files || !input.files[0]) return;
            playAnimusSound();
            document.getElementById('uploadBox').style.display = 'none';
            document.querySelector('.gender-selector').style.display = 'none';
            document.getElementById('loaderScreen').style.display = 'block';

            const formData = new FormData();
            formData.append('file', input.files[0]);
            formData.append('gender', selectedGender);
            formData.append('user_id', tgUser.id);
            formData.append('user_name', tgUser.name);
            formData.append('user_username', tgUser.username);

            try {
                const response = await fetch('/analyze', { method: 'POST', body: formData });
                const data = await response.json();
                if (data.id) window.location.href = '/result/' + data.id;
            } catch (err) {
                alert('Десинхронизация с сервером');
                location.reload();
            }
        }

        function shareResult() {
            const currentUrl = window.location.href;
            const text = "🔥 Мой результат биометрического анализа лица в Animus Matrix! Посмотри карточку:";
            const shareUrl = "https://t.me/share/url?url=" + encodeURIComponent(currentUrl) + "&text=" + encodeURIComponent(text);
            if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.openTelegramLink) {
                window.Telegram.WebApp.openTelegramLink(shareUrl);
            } else {
                window.open(shareUrl, '_blank');
            }
        }

        {% if data %}
        const rating = {{ data.rating }};
        const gaugeBar = document.getElementById('gaugeBar');
        const scoreNum = document.getElementById('scoreNum');

        gaugeBar.style.stroke = "{{ data.color_hex }}";
        const offset = (2 * Math.PI * 90) - (rating / 10.0) * (2 * Math.PI * 90);

        setTimeout(() => {
            gaugeBar.style.strokeDashoffset = offset;
            document.getElementById('symBar').style.width = "{{ data.details.symmetry }}%";
            document.getElementById('sharpBar').style.width = "{{ (data.details.sharpness * 10.0) }}%";
            document.getElementById('harmBar').style.width = "{{ (data.details.harmony * 10.0) }}%";
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
    </script>
</body>
</html>
"""

# ==============================================================================
# 🛰 ROUTES (FLASK + ОТПРАВКА СНИМКОВ АДМИНУ)
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
                        f"📊 **Рейтинг ДНК:** `{rating}/10` ({category})"
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

# Запуск бота в фоновом потоке
threading.Thread(target=start_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
