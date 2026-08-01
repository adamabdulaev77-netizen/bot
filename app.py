# ==============================================================================
# 🌐 AESTHETIC VISION AI — FLASK WEB APP & OPENCV ENGINE (RENDER READY)
# ==============================================================================
# Зависимости для Render (файл requirements.txt):
# Flask
# opencv-python-headless
# numpy
# Pillow
# gunicorn
# ==============================================================================

import os
import uuid
import time
import math
import cv2
import numpy as np
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__, static_folder='static')

# Настройка папки загрузок
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Хранилище результатов в памяти
results_db = {}

# ==============================================================================
# 🎨 ИНТЕРАКТИВНЫЙ ФРОНТЕНД (GLASSMORPHISM + CANVAS 3D + TELEGRAM MINI APP)
# ==============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Aesthetic Vision AI — Mini App</title>
    <!-- Telegram WebApp SDK -->
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #050508;
            --accent-purple: #8b5cf6;
            --accent-pink: #ec4899;
            --glass-bg: rgba(255, 255, 255, 0.03);
            --glass-border: rgba(255, 255, 255, 0.08);
            --glass-card: rgba(18, 18, 26, 0.65);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            -webkit-tap-highlight-color: transparent;
            user-select: none;
        }

        body {
            background: var(--bg-base);
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow-x: hidden;
            position: relative;
            padding: 16px 12px;
        }

        /* Анимированные Фоновые Холсты */
        #particles-canvas, #confetti-canvas {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
        }
        #particles-canvas { z-index: 0; }
        #confetti-canvas { z-index: 100; }

        /* Фоновый неоновый градиент */
        .glow-sphere {
            position: fixed;
            border-radius: 50%;
            filter: blur(120px);
            opacity: 0.35;
            pointer-events: none;
            z-index: 1;
        }
        .glow-1 {
            top: -10%;
            left: -10%;
            width: 350px;
            height: 350px;
            background: radial-gradient(circle, #7c3aed, transparent);
        }
        .glow-2 {
            bottom: -10%;
            right: -10%;
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, #db2777, transparent);
        }

        /* Главный контейнер карточки */
        .app-container {
            position: relative;
            z-index: 10;
            width: 100%;
            max-width: 480px;
            background: var(--glass-card);
            backdrop-filter: blur(30px);
            -webkit-backdrop-filter: blur(30px);
            border: 1px solid var(--glass-border);
            border-radius: 32px;
            padding: 28px 20px;
            box-shadow: 0 30px 70px rgba(0, 0, 0, 0.8),
                        inset 0 1px 0 rgba(255, 255, 255, 0.1);
            animation: appAppear 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        @keyframes appAppear {
            from { opacity: 0; transform: translateY(30px) scale(0.97); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }

        /* Шапка */
        .header {
            text-align: center;
            margin-bottom: 24px;
        }
        .header .logo-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 20px;
            background: rgba(139, 92, 246, 0.12);
            border: 1px solid rgba(139, 92, 246, 0.3);
            font-size: 0.75rem;
            font-weight: 700;
            color: #c084fc;
            letter-spacing: 1px;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .header h1 {
            font-size: 1.9rem;
            font-weight: 900;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header p {
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.5);
            margin-top: 4px;
            font-weight: 500;
        }

        /* Блок Загрузки Фото */
        .upload-zone {
            border: 2px dashed rgba(255, 255, 255, 0.18);
            border-radius: 24px;
            padding: 35px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
            background: rgba(255, 255, 255, 0.015);
            position: relative;
            overflow: hidden;
        }
        .upload-zone:hover, .upload-zone:active {
            border-color: var(--accent-purple);
            background: rgba(139, 92, 246, 0.06);
            transform: translateY(-2px);
        }
        .upload-icon-wrapper {
            width: 70px;
            height: 70px;
            margin: 0 auto 16px;
            border-radius: 50%;
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(236, 72, 153, 0.2));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
        }
        .upload-title {
            font-size: 1.1rem;
            font-weight: 800;
            color: #ffffff;
            margin-bottom: 6px;
        }
        .upload-subtitle {
            font-size: 0.8rem;
            color: rgba(255, 255, 255, 0.45);
            margin-bottom: 18px;
        }
        .btn-select {
            display: inline-block;
            background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
            color: #ffffff;
            padding: 12px 28px;
            border-radius: 14px;
            font-weight: 700;
            font-size: 0.9rem;
            box-shadow: 0 8px 20px rgba(139, 92, 246, 0.35);
            transition: all 0.2s ease;
        }
        #fileInput { display: none; }

        /* Лоадер при анализе */
        .loading-state {
            display: none;
            text-align: center;
            padding: 30px 10px;
        }
        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid rgba(255, 255, 255, 0.1);
            border-left-color: var(--accent-purple);
            border-top-color: var(--accent-pink);
            border-radius: 50%;
            margin: 0 auto 16px;
            animation: spin 0.9s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loading-text {
            font-size: 0.95rem;
            font-weight: 700;
            color: #e2e8f0;
        }

        /* Экран Результата */
        .result-screen {
            display: none;
            flex-direction: column;
            align-items: center;
            gap: 22px;
        }
        .preview-container {
            width: 100%;
            max-height: 260px;
            border-radius: 20px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.12);
            position: relative;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
            background: #000000;
        }
        .preview-container img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }

        /* Круговой Прогресс Бар */
        .score-gauge {
            position: relative;
            width: 180px;
            height: 180px;
        }
        .score-gauge svg {
            width: 100%;
            height: 100%;
            transform: rotate(-90deg);
        }
        .gauge-bg {
            fill: none;
            stroke: rgba(255, 255, 255, 0.05);
            stroke-width: 14;
        }
        .gauge-bar {
            fill: none;
            stroke-width: 14;
            stroke-linecap: round;
            stroke-dasharray: 565.48;
            stroke-dashoffset: 565.48;
            transition: stroke-dashoffset 1.8s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .gauge-content {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
        }
        .score-num {
            font-size: 3.5rem;
            font-weight: 900;
            line-height: 1;
            letter-spacing: -1px;
        }
        .score-sub {
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.4);
            font-weight: 700;
            margin-top: 2px;
            text-transform: uppercase;
        }

        /* Бейдж Категории */
        .category-pill {
            padding: 12px 30px;
            border-radius: 100px;
            font-size: 1.4rem;
            font-weight: 900;
            letter-spacing: 2px;
            text-transform: uppercase;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            border: 1px solid rgba(255, 255, 255, 0.2);
            animation: badgeGlow 2s infinite alternate ease-in-out;
        }
        @keyframes badgeGlow {
            from { transform: scale(1); }
            to { transform: scale(1.04); }
        }

        /* Цветовые стили категорий */
        .cat-SUB3 { color: #ff4d4d; border-color: #ff4d4d; box-shadow: 0 0 30px rgba(255,77,77,0.3); }
        .cat-SUB5 { color: #ff944d; border-color: #ff944d; box-shadow: 0 0 30px rgba(255,148,77,0.3); }
        .cat-LTN  { color: #ffd11a; border-color: #ffd11a; box-shadow: 0 0 30px rgba(255,209,26,0.3); }
        .cat-MTN  { color: #a6ff1a; border-color: #a6ff1a; box-shadow: 0 0 30px rgba(166,255,26,0.3); }
        .cat-HTN  { color: #2eb82e; border-color: #2eb82e; box-shadow: 0 0 30px rgba(46,184,46,0.3); }
        .cat-CHAD { color: #00ccff; border-color: #00ccff; box-shadow: 0 0 35px rgba(0,204,255,0.4); }
        .cat-TRUE_ADAM { 
            color: #ffd700; 
            border-color: #ffd700; 
            background: linear-gradient(135deg, rgba(255,215,0,0.25), rgba(255,140,0,0.25));
            box-shadow: 0 0 50px rgba(255,215,0,0.9);
            animation: goldGlow 1.2s infinite alternate ease-in-out;
        }
        @keyframes goldGlow {
            from { box-shadow: 0 0 20px rgba(255,215,0,0.6); }
            to { box-shadow: 0 0 50px rgba(255,215,0,1); }
        }

        /* Метрики и бары параметров */
        .metrics-card {
            width: 100%;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 18px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .metric-item {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .metric-header {
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            font-weight: 700;
        }
        .metric-title { color: rgba(255, 255, 255, 0.6); }
        .metric-val { color: #ffffff; }
        .progress-track {
            height: 6px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            overflow: hidden;
            position: relative;
        }
        .progress-fill {
            height: 100%;
            border-radius: 10px;
            width: 0%;
            transition: width 1.5s cubic-bezier(0.16, 1, 0.3, 1);
        }

        /* Кнопка Повтора */
        .btn-restart {
            width: 100%;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.12);
            color: #ffffff;
            padding: 14px;
            border-radius: 16px;
            font-weight: 800;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-top: 5px;
        }
        .btn-restart:active {
            transform: scale(0.98);
            background: rgba(255, 255, 255, 0.1);
        }
    </style>
</head>
<body>
    <div class="glow-sphere glow-1"></div>
    <div class="glow-sphere glow-2"></div>

    <canvas id="particles-canvas"></canvas>
    <canvas id="confetti-canvas"></canvas>

    <div class="app-container">
        <div class="header">
            <div class="logo-badge">⚡ Computer Vision v2.4</div>
            <h1>Aesthetic Vision AI</h1>
            <p>Векторный анализ нейросетью геометрии лица</p>
        </div>

        {% if not data %}
        <!-- ЭКРАН 1: ЗАГРУЗКА СНИМКА -->
        <div class="upload-zone" id="uploadZone" onclick="document.getElementById('fileInput').click()">
            <div class="upload-icon-wrapper">📸</div>
            <div class="upload-title">Загрузи свое фото</div>
            <div class="upload-subtitle">Выбери селфи или портрет из галереи</div>
            <div class="btn-select">Выбрать снимок</div>
            <input type="file" id="fileInput" accept="image/*" onchange="processFileUpload(this)">
        </div>

        <div class="loading-state" id="loadingState">
            <div class="spinner"></div>
            <div class="loading-text">Сканирование векторов и геометрии...</div>
        </div>
        {% endif %}

        <!-- ЭКРАН 2: РЕЗУЛЬТАТЫ -->
        <div class="result-screen" id="resultScreen" style="{% if data %}display:flex;{% endif %}">
            <div class="preview-container">
                <img id="resImage" src="{% if data %}/static/uploads/{{ data.image_filename }}{% endif %}" alt="Face Scan">
            </div>

            <div class="score-gauge">
                <svg viewBox="0 0 200 200">
                    <circle class="gauge-bg" cx="100" cy="100" r="90"></circle>
                    <circle class="gauge-bar" id="gaugeBar" cx="100" cy="100" r="90"></circle>
                </svg>
                <div class="gauge-content">
                    <div class="score-num" id="scoreNum">{% if data %}{{ data.rating }}{% else %}0{% endif %}</div>
                    <div class="score-sub">балла из 10</div>
                </div>
            </div>

            <div class="category-pill {% if data %}{{ data.cat_class }}{% endif %}" id="catBadge">
                {% if data %}{{ data.category }}{% endif %}
            </div>

            <div class="metrics-card">
                <div class="metric-item">
                    <div class="metric-header">
                        <span class="metric-title">Симметрия овала лица</span>
                        <span class="metric-val" id="symVal">{% if data %}{{ data.details.symmetry }}%{% else %}0%{% endif %}</span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-fill" id="symBar" style="background: linear-gradient(90deg, #8b5cf6, #c084fc);"></div>
                    </div>
                </div>

                <div class="metric-item">
                    <div class="metric-header">
                        <span class="metric-title">Резкость и детализация</span>
                        <span class="metric-val" id="sharpVal">{% if data %}{{ data.details.sharpness }}/10{% else %}0/10{% endif %}</span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-fill" id="sharpBar" style="background: linear-gradient(90deg, #3b82f6, #60a5fa);"></div>
                    </div>
                </div>

                <div class="metric-item">
                    <div class="metric-header">
                        <span class="metric-title">Цветовая гармония</span>
                        <span class="metric-val" id="harmVal">{% if data %}{{ data.details.harmony }}/10{% else %}0/10{% endif %}</span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-fill" id="harmBar" style="background: linear-gradient(90deg, #ec4899, #f472b6);"></div>
                    </div>
                </div>
            </div>

            <button class="btn-restart" onclick="location.href='/'">🔄 Проверить другое фото</button>
        </div>
    </div>

    <script>
        // Инициализация Telegram WebApp
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
        }

        // Canvas Частицы на фоне
        const pCanvas = document.getElementById('particles-canvas');
        const pCtx = pCanvas.getContext('2d');
        let particles = [];

        function resizeP() {
            pCanvas.width = window.innerWidth;
            pCanvas.height = window.innerHeight;
        }
        window.addEventListener('resize', resizeP);
        resizeP();

        class Particle {
            constructor() {
                this.x = Math.random() * pCanvas.width;
                this.y = Math.random() * pCanvas.height;
                this.size = Math.random() * 2 + 0.5;
                this.speedX = (Math.random() - 0.5) * 0.3;
                this.speedY = (Math.random() - 0.5) * 0.3;
                this.opacity = Math.random() * 0.5 + 0.2;
            }
            update() {
                this.x += this.speedX;
                this.y += this.speedY;
                if (this.x < 0) this.x = pCanvas.width;
                if (this.x > pCanvas.width) this.x = 0;
                if (this.y < 0) this.y = pCanvas.height;
                if (this.y > pCanvas.height) this.y = 0;
            }
            draw() {
                pCtx.fillStyle = `rgba(192, 132, 252, ${this.opacity})`;
                pCtx.beginPath();
                pCtx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                pCtx.fill();
            }
        }
        for (let i = 0; i < 55; i++) particles.push(new Particle());

        function animP() {
            pCtx.clearRect(0, 0, pCanvas.width, pCanvas.height);
            particles.forEach(p => { p.update(); p.draw(); });
            requestAnimationFrame(animP);
        }
        animP();

        // Функция отправки файла
        async function processFileUpload(input) {
            if (!input.files || !input.files[0]) return;
            
            document.getElementById('uploadZone').style.display = 'none';
            document.getElementById('loadingState').style.display = 'block';

            const formData = new FormData();
            formData.append('file', input.files[0]);

            try {
                const response = await fetch('/analyze', { method: 'POST', body: formData });
                const result = await response.json();

                if (result.id) {
                    window.location.href = '/result/' + result.id;
                } else {
                    alert('Ошибка анализа изображения!');
                    location.reload();
                }
            } catch (err) {
                alert('Не удалось подключиться к серверу.');
                location.reload();
            }
        }

        {% if data %}
        // Анимация при отрисовке результатов
        const rating = {{ data.rating }};
        const colorHex = "{{ data.color_hex }}";
        const gaugeBar = document.getElementById('gaugeBar');
        
        gaugeBar.style.stroke = colorHex;
        const radius = 90;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (rating / 10) * circumference;

        setTimeout(() => {
            gaugeBar.style.strokeDashoffset = offset;
            document.getElementById('symBar').style.width = "{{ data.details.symmetry }}%";
            document.getElementById('sharpBar').style.width = "{{ (data.details.sharpness * 10) }}%";
            document.getElementById('harmBar').style.width = "{{ (data.details.harmony * 10) }}%";
        }, 150);

        {% if data.category == "TRUE ADAM" %}
        // Эффект Золотого Конфетти для категории TRUE ADAM
        const cCanvas = document.getElementById('confetti-canvas');
        const cCtx = cCanvas.getContext('2d');
        cCanvas.width = window.innerWidth;
        cCanvas.height = window.innerHeight;

        let confetti = [];
        const goldShades = ['#ffd700', '#ffae00', '#fff8dc', '#e6c200', '#ffffff'];

        for (let i = 0; i < 180; i++) {
            confetti.push({
                x: Math.random() * cCanvas.width,
                y: Math.random() * cCanvas.height - cCanvas.height,
                size: Math.random() * 8 + 4,
                color: goldShades[Math.floor(Math.random() * goldShades.length)],
                speedY: Math.random() * 5 + 2,
                speedX: (Math.random() - 0.5) * 2.5,
                rot: Math.random() * 360,
                rotSpeed: Math.random() * 8 - 4
            });
        }

        function animConfetti() {
            cCtx.clearRect(0, 0, cCanvas.width, cCanvas.height);
            confetti.forEach(c => {
                c.y += c.speedY;
                c.x += c.speedX;
                c.rot += c.rotSpeed;
                if (c.y > cCanvas.height) c.y = -15;
                
                cCtx.save();
                cCtx.translate(c.x, c.y);
                cCtx.rotate((c.rot * Math.PI) / 180);
                cCtx.fillStyle = c.color;
                cCtx.fillRect(-c.size / 2, -c.size / 2, c.size, c.size);
                cCtx.restore();
            });
            requestAnimationFrame(animConfetti);
        }
        animConfetti();
        {% endif %}
        {% endif %}
    </script>
</body>
</html>
"""

# ==============================================================================
# 🔬 OPENCV ОБРАБОТКА ФОТОГРАФИИ
# ==============================================================================
def analyze_face_opencv(image_path: str):
    img = cv2.imread(image_path)
    if img is None:
        return 5, "LTN", "cat-LTN", "#ffd11a", {"symmetry": 50, "sharpness": 5.0, "harmony": 5.0}

    # Оптимизация размера изображения
    h, w = img.shape[:2]
    max_dim = 800
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1. Симметрия
    mid_x = gray.shape[1] // 2
    left_side = gray[:, :mid_x]
    right_side = gray[:, mid_x:mid_x + left_side.shape[1]]
    right_side_flipped = cv2.flip(right_side, 1)

    min_h = min(left_side.shape[0], right_side_flipped.shape[0])
    min_w = min(left_side.shape[1], right_side_flipped.shape[1])

    diff = cv2.absdiff(left_side[:min_h, :min_w], right_side_flipped[:min_h, :min_w])
    symmetry_pct = round(max(35.0, min(99.0, 100.0 - (np.mean(diff) * 0.85))), 1)
    symmetry_score = symmetry_pct / 10.0

    # 2. Резкость
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    sharpness_score = min(10.0, max(1.0, math.log1p(laplacian_var) * 1.45))
    sharpness_val = round(sharpness_score, 1)

    # 3. Цветовой баланс
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    harmony_score = min(10.0, max(1.0, (np.mean(hsv[:, :, 1]) / 25.5) * 0.5 + (np.mean(hsv[:, :, 2]) / 25.5) * 0.5))
    harmony_val = round(harmony_score, 1)

    # Итоговый рейтинг
    raw_score = (symmetry_score * 0.50) + (sharpness_score * 0.30) + (harmony_score * 0.20)
    rating = int(np.clip(round(raw_score), 1, 10))

    categories = {
        1: ("SUB 3", "cat-SUB3", "#ff4d4d"),
        2: ("SUB 3", "cat-SUB3", "#ff4d4d"),
        3: ("SUB 5", "cat-SUB5", "#ff944d"),
        4: ("SUB 5", "cat-SUB5", "#ff944d"),
        5: ("LTN", "cat-LTN", "#ffd11a"),
        6: ("MTN", "cat-MTN", "#a6ff1a"),
        7: ("HTN", "cat-HTN", "#2eb82e"),
        8: ("CHAD", "cat-CHAD", "#00ccff"),
        9: ("CHAD", "cat-CHAD", "#00ccff"),
        10: ("TRUE ADAM", "cat-TRUE_ADAM", "#ffd700")
    }

    category, cat_class, color_hex = categories.get(rating, ("LTN", "cat-LTN", "#ffd11a"))
    
    details = {
        "symmetry": symmetry_pct,
        "sharpness": sharpness_val,
        "harmony": harmony_val
    }

    return rating, category, cat_class, color_hex, details

# ==============================================================================
# 🛰 ЭНДПОИНТЫ FLASK СЕРВЕРА
# ==============================================================================
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, data=None)

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    unique_id = f"{uuid.uuid4().hex}_{int(time.time())}"
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{unique_id}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    file.save(filepath)

    rating, category, cat_class, color_hex, details = analyze_face_opencv(filepath)

    results_db[unique_id] = {
        "rating": rating,
        "category": category,
        "cat_class": cat_class,
        "color_hex": color_hex,
        "details": details,
        "image_filename": filename
    }

    return jsonify({
        "rating": rating,
        "category": category,
        "id": unique_id
    })

@app.route('/result/<result_id>')
def show_result(result_id):
    data = results_db.get(result_id)
    if not data:
        return render_template_string(HTML_TEMPLATE, data=None)
    return render_template_string(HTML_TEMPLATE, data=data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)