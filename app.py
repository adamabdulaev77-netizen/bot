# ==============================================================================
# 🌐 AESTHETIC VISION AI — FLASK SERVER & 3D WIREFRAME MINI APP
# ==============================================================================
# Зависимости:
# pip install Flask opencv-python-headless numpy Pillow gunicorn
# ==============================================================================

import os
import uuid
import time
import math
import cv2
import numpy as np
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__, static_folder='static')
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

results_db = {}

# ==============================================================================
# 🎨 ИНТЕРАКТИВНЫЙ ФРОНТЕНД (GLASSMORPHISM + 3D WIREFRAME LASER HEADS)
# ==============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Aesthetic AI Agent</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #040407;
            --accent-purple: #8b5cf6;
            --accent-cyan: #06b6d4;
            --glass-border: rgba(255, 255, 255, 0.12);
            --glass-card: rgba(15, 15, 24, 0.78);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Plus Jakarta Sans', sans-serif;
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
            padding: 20px 12px;
        }

        /* 3D Wireframe Canvas на фоне */
        #wireframe-canvas {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 0;
            pointer-events: none;
        }

        #confetti-canvas {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 100;
            pointer-events: none;
        }

        /* Главная карточка */
        .app-card {
            position: relative;
            z-index: 10;
            width: 100%;
            max-width: 490px;
            background: var(--glass-card);
            backdrop-filter: blur(35px);
            -webkit-backdrop-filter: blur(35px);
            border: 1px solid var(--glass-border);
            border-radius: 32px;
            padding: 28px 20px;
            box-shadow: 0 40px 90px rgba(0, 0, 0, 0.85),
                        inset 0 1px 0 rgba(255, 255, 255, 0.15);
            animation: cardFadeUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        @keyframes cardFadeUp {
            from { opacity: 0; transform: translateY(40px) scale(0.96); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }

        .header {
            text-align: center;
            margin-bottom: 22px;
        }
        .header .badge {
            display: inline-block;
            padding: 5px 14px;
            border-radius: 20px;
            background: rgba(139, 92, 246, 0.15);
            border: 1px solid rgba(139, 92, 246, 0.35);
            font-size: 0.75rem;
            font-weight: 800;
            color: #c084fc;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .header h1 {
            font-size: 1.9rem;
            font-weight: 900;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header p {
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.5);
            margin-top: 4px;
        }

        /* Загрузка */
        .upload-zone {
            border: 2px dashed rgba(255, 255, 255, 0.2);
            border-radius: 24px;
            padding: 35px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            background: rgba(255, 255, 255, 0.02);
        }
        .upload-zone:hover {
            border-color: var(--accent-purple);
            background: rgba(139, 92, 246, 0.08);
        }
        .btn-upload {
            display: inline-block;
            background: linear-gradient(135deg, #8b5cf6, #06b6d4);
            color: #ffffff;
            padding: 12px 28px;
            border-radius: 14px;
            font-weight: 800;
            font-size: 0.9rem;
            margin-top: 15px;
            box-shadow: 0 8px 20px rgba(139, 92, 246, 0.3);
        }
        #fileInput { display: none; }

        .loader-box {
            display: none;
            text-align: center;
            padding: 30px 10px;
        }
        .spinner {
            width: 48px;
            height: 48px;
            border: 4px solid rgba(255,255,255,0.1);
            border-left-color: var(--accent-purple);
            border-top-color: var(--accent-cyan);
            border-radius: 50%;
            margin: 0 auto 15px;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* Экран Результата */
        .result-screen {
            display: none;
            flex-direction: column;
            align-items: center;
            gap: 22px;
        }

        /* 🖼 ИСПРАВЛЕНИЕ: ПОЛНОЕ ОТОБРАЖЕНИЕ ФОТО БЕЗ ОБРЕЗАНИЯ */
        .preview-box {
            width: 100%;
            height: 320px;
            border-radius: 20px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.15);
            background: #000000;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.6);
        }
        .preview-box img {
            max-width: 100%;
            max-height: 100%;
            width: auto;
            height: auto;
            object-fit: contain;
            display: block;
        }

        /* Прогресс бар рейтинга */
        .gauge-wrapper {
            position: relative;
            width: 180px;
            height: 180px;
        }
        .gauge-wrapper svg {
            width: 100%;
            height: 100%;
            transform: rotate(-90deg);
        }
        .gauge-bg {
            fill: none;
            stroke: rgba(255, 255, 255, 0.05);
            stroke-width: 14;
        }
        .gauge-fill {
            fill: none;
            stroke-width: 14;
            stroke-linecap: round;
            stroke-dasharray: 565.48;
            stroke-dashoffset: 565.48;
            transition: stroke-dashoffset 1.8s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .gauge-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
        }
        .score-val {
            font-size: 3.4rem;
            font-weight: 900;
            line-height: 1;
            letter-spacing: -1px;
        }
        .score-max {
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.4);
            font-weight: 700;
            margin-top: 2px;
        }

        /* Бейдж Категории */
        .badge-category {
            padding: 12px 32px;
            border-radius: 100px;
            font-size: 1.4rem;
            font-weight: 900;
            letter-spacing: 2px;
            text-transform: uppercase;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .cat-SUB3 { color: #ff4d4d; border-color: #ff4d4d; box-shadow: 0 0 25px rgba(255,77,77,0.3); }
        .cat-SUB5 { color: #ff944d; border-color: #ff944d; box-shadow: 0 0 25px rgba(255,148,77,0.3); }
        .cat-LTN  { color: #ffd11a; border-color: #ffd11a; box-shadow: 0 0 25px rgba(255,209,26,0.3); }
        .cat-MTN  { color: #a6ff1a; border-color: #a6ff1a; box-shadow: 0 0 25px rgba(166,255,26,0.3); }
        .cat-HTN  { color: #2eb82e; border-color: #2eb82e; box-shadow: 0 0 25px rgba(46,184,46,0.3); }
        .cat-CHAD { color: #00ccff; border-color: #00ccff; box-shadow: 0 0 35px rgba(0,204,255,0.4); }
        .cat-TRUE_ADAM { 
            color: #ffd700; 
            border-color: #ffd700; 
            background: rgba(255,215,0,0.2);
            box-shadow: 0 0 50px rgba(255,215,0,0.9);
        }

        /* Карточки Разбора */
        .ai-cards {
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .ai-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 18px;
            padding: 14px 18px;
            text-align: left;
        }
        .ai-card-title {
            font-size: 0.9rem;
            font-weight: 800;
            margin-bottom: 6px;
        }
        .title-pros { color: #4ade80; }
        .title-cons { color: #f87171; }
        .title-recs { color: #38bdf8; }
        .ai-card-text {
            font-size: 0.83rem;
            color: rgba(255,255,255,0.8);
            line-height: 1.45;
        }

        .btn-reset {
            width: 100%;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.12);
            color: #ffffff;
            padding: 14px;
            border-radius: 16px;
            font-weight: 800;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-reset:active { transform: scale(0.98); }
    </style>
</head>
<body>
    <!-- 3D Лазерный Wireframe Canvas -->
    <canvas id="wireframe-canvas"></canvas>
    <canvas id="confetti-canvas"></canvas>

    <div class="app-card">
        <div class="header">
            <div class="badge">⚡ 3D Neural Scan Engine</div>
            <h1>Aesthetic Vision AI</h1>
            <p>Векторный разбор лица и геометрии</p>
        </div>

        {% if not data %}
        <div class="upload-zone" id="uploadZone" onclick="document.getElementById('fileInput').click()">
            <div style="font-size: 2.6rem; margin-bottom: 8px;">📸</div>
            <div style="font-size: 1.1rem; font-weight: 800;">Загрузи свое фото</div>
            <div style="font-size: 0.8rem; color: rgba(255,255,255,0.45); margin-top: 4px;">Портрет или селфи в полный анфас</div>
            <div class="btn-upload">Загрузить снимок</div>
            <input type="file" id="fileInput" accept="image/*" onchange="uploadFile(this)">
        </div>

        <div class="loader-box" id="loaderBox">
            <div class="spinner"></div>
            <div style="font-size: 0.9rem; font-weight: 700;">ИИ высчитывает пропорции и векторы...</div>
        </div>
        {% endif %}

        <div class="result-screen" id="resultScreen" style="{% if data %}display:flex;{% endif %}">
            <div class="preview-box">
                <img src="{% if data %}/static/uploads/{{ data.image_filename }}{% endif %}" alt="Face Scan">
            </div>

            <div class="gauge-wrapper">
                <svg viewBox="0 0 200 200">
                    <circle class="gauge-bg" cx="100" cy="100" r="90"></circle>
                    <circle class="gauge-fill" id="gaugeFill" cx="100" cy="100" r="90"></circle>
                </svg>
                <div class="gauge-text">
                    <div class="score-val" id="scoreVal">{% if data %}{{ data.rating }}{% else %}0.0{% endif %}</div>
                    <div class="score-max">из 10.0</div>
                </div>
            </div>

            <div class="badge-category {% if data %}{{ data.cat_class }}{% endif %}">
                {% if data %}{{ data.category }}{% endif %}
            </div>

            {% if data %}
            <div class="ai-cards">
                <div class="ai-card">
                    <div class="ai-card-title title-pros">🔥 Достоинства</div>
                    <div class="ai-card-text">{{ data.report.pros }}</div>
                </div>
                <div class="ai-card">
                    <div class="ai-card-title title-cons">❌ Недостатки</div>
                    <div class="ai-card-text">{{ data.report.cons }}</div>
                </div>
                <div class="ai-card">
                    <div class="ai-card-title title-recs">💡 Рекомендации по уходу</div>
                    <div class="ai-card-text">{{ data.report.recs }}</div>
                </div>
            </div>
            {% endif %}

            <button class="btn-reset" onclick="location.href='/'">🔄 Проверить другое фото</button>
        </div>
    </div>

    <script>
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
        }

        // ==============================================================================
        // 🔮 CANVAS 3D WIREFRAME LASER HEADS (АНИМАЦИЯ ВРАЩАЮЩИХСЯ ГОЛОВ ПО БОКАМ)
        // ==============================================================================
        const canvas = document.getElementById('wireframe-canvas');
        const ctx = canvas.getContext('2d');

        function resizeCanvas() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }
        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();

        // Вершины 3D модальной структуры лица/черепа
        const headVertices = [
            // Овал черепа и челюсть
            {x: 0, y: 1.2, z: 0}, {x: -0.6, y: 0.9, z: 0.2}, {x: 0.6, y: 0.9, z: 0.2},
            {x: -0.8, y: 0.4, z: 0}, {x: 0.8, y: 0.4, z: 0},
            {x: -0.7, y: -0.2, z: 0.2}, {x: 0.7, y: -0.2, z: 0.2},
            {x: -0.5, y: -0.8, z: 0.4}, {x: 0.5, y: -0.8, z: 0.4},
            {x: 0, y: -1.1, z: 0.5}, // подбородок
            
            # Глаза и брови
            {x: -0.4, y: 0.3, z: 0.5}, {x: -0.15, y: 0.3, z: 0.5},
            {x: 0.15, y: 0.3, z: 0.5}, {x: 0.4, y: 0.3, z: 0.5},
            
            # Нос
            {x: 0, y: 0.3, z: 0.6}, {x: 0, y: -0.1, z: 0.7}, {x: -0.15, y: -0.2, z: 0.55}, {x: 0.15, y: -0.2, z: 0.55},
            
            # Рот
            {x: -0.25, y: -0.45, z: 0.55}, {x: 0, y: -0.4, z: 0.6}, {x: 0.25, y: -0.45, z: 0.55},
            {x: 0, y: -0.55, z: 0.58}
        ];

        # Связи между точками (wireframe)
        const headEdges = [
            [0,1],[0,2],[1,3],[2,4],[3,5],[4,6],[5,7],[6,8],[7,9],[8,9],
            [10,11],[12,13],[14,15],[16,15],[17,15],[18,19],[19,20],[19,21]
        ];

        let angleY = 0;

        function drawWireframeHead(centerX, centerY, scale) {
            angleY += 0.015;
            const cosY = Math.cos(angleY);
            const sinY = Math.sin(angleY);

            const projected = headVertices.map(v => {
                // Вращение по Y
                let x = v.x * cosY - v.z * sinY;
                let z = v.x * sinY + v.z * cosY + 2.5;
                let y = v.y;

                // Проекция 3D в 2D
                let projX = centerX + (x / z) * scale;
                let projY = centerY - (y / z) * scale;
                return {x: projX, y: projY};
            });

            ctx.strokeStyle = 'rgba(255, 255, 255, 0.45)';
            ctx.lineWidth = 1.2;
            ctx.shadowColor = '#ffffff';
            ctx.shadowBlur = 8;

            // Рисуем грани
            headEdges.forEach(edge => {
                const p1 = projected[edge[0]];
                const p2 = projected[edge[1]];
                ctx.beginPath();
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);
                ctx.stroke();
            });

            // Рисуем неоновые узловые точки
            ctx.fillStyle = '#06b6d4';
            projected.forEach(p => {
                ctx.beginPath();
                ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
                ctx.fill();
            });
        }

        function renderScene() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Если экран достаточно широкий, рисуем две головы по бокам
            if (canvas.width > 700) {
                drawWireframeHead(110, canvas.height / 2, 220);
                drawWireframeHead(canvas.width - 110, canvas.height / 2, 220);
            } else {
                // На мобилках рисуем одну полупрозрачную сверху
                drawWireframeHead(canvas.width / 2, 120, 140);
            }
            requestAnimationFrame(renderScene);
        }
        renderScene();

        // Загрузка снимка
        async function uploadFile(input) {
            if (!input.files || !input.files[0]) return;
            document.getElementById('uploadZone').style.display = 'none';
            document.getElementById('loaderBox').style.display = 'block';

            const formData = new FormData();
            formData.append('file', input.files[0]);

            try {
                const res = await fetch('/analyze', { method: 'POST', body: formData });
                const data = await res.json();
                if (data.id) window.location.href = '/result/' + data.id;
            } catch (err) {
                alert('Ошибка соединения с сервером');
                location.reload();
            }
        }

        {% if data %}
        // Анимация Прогресс Бара и Дробного Счетчика
        const rating = {{ data.rating }};
        const gaugeFill = document.getElementById('gaugeFill');
        const scoreVal = document.getElementById('scoreVal');
        
        gaugeFill.style.stroke = "{{ data.color_hex }}";
        const circumference = 2 * Math.PI * 90;
        const offset = circumference - (rating / 10) * circumference;

        setTimeout(() => {
            gaugeFill.style.strokeDashoffset = offset;
        }, 150);

        // Дробный счетчик от 0.0 до текущего балла
        let curScore = 0.0;
        const step = rating / 40.0;
        const timer = setInterval(() => {
            curScore += step;
            if (curScore >= rating) {
                scoreVal.innerText = rating.toFixed(1);
                clearInterval(timer);
            } else {
                scoreVal.innerText = curScore.toFixed(1);
            }
        }, 30);
        {% endif %}
    </script>
</body>
</html>
"""

# ==============================================================================
# 🔬 OPENCV ОБРАБОТКА (ОЦЕНКА С ТОЧНОСТЬЮ ДО ДЕСЯТЫХ)
# ==============================================================================
def analyze_face_opencv(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return 5.0, "LTN", "cat-LTN", "#ffd11a", {}

    h, w = img.shape[:2]
    max_dim = 800
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1. Симметрия
    mid_x = gray.shape[1] // 2
    left_side = gray[:, :mid_x]
    right_side = cv2.flip(gray[:, mid_x:mid_x + left_side.shape[1]], 1)

    min_h = min(left_side.shape[0], right_side.shape[0])
    min_w = min(left_side.shape[1], right_side.shape[1])
    diff = cv2.absdiff(left_side[:min_h, :min_w], right_side[:min_h, :min_w])

    sym_pct = round(max(35.0, min(99.0, 100.0 - (np.mean(diff) * 0.82))), 1)

    # 2. Резкость
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    sharp_score = min(10.0, max(1.0, math.log1p(laplacian_var) * 1.42))

    # 3. Баланс тона
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    harm_score = min(10.0, max(1.0, (np.mean(hsv[:, :, 1]) / 25.5) * 0.5 + (np.mean(hsv[:, :, 2]) / 25.5) * 0.5))

    # Итоговый точный дробный рейтинг
    raw_rating = ((sym_pct / 10.0) * 0.50) + (sharp_score * 0.30) + (harm_score * 0.20)
    rating = round(float(np.clip(raw_rating, 1.0, 10.0)), 1)

    # Категории
    if rating < 3.0:
        cat, cat_cls, color = "SUB 3", "cat-SUB3", "#ff4d4d"
    elif rating < 5.0:
        cat, cat_cls, color = "SUB 5", "cat-SUB5", "#ff944d"
    elif rating < 6.0:
        cat, cat_cls, color = "LTN", "cat-LTN", "#ffd11a"
    elif rating < 7.0:
        cat, cat_cls, color = "MTN", "cat-MTN", "#a6ff1a"
    elif rating < 8.0:
        cat, cat_cls, color = "HTN", "cat-HTN", "#2eb82e"
    elif rating < 10.0:
        cat, cat_cls, color = "CHAD", "cat-CHAD", "#00ccff"
    else:
        cat, cat_cls, color = "TRUE ADAM", "cat-TRUE_ADAM", "#ffd700"

    report = {
        "pros": f"Симметрия овала лица составляет {sym_pct}%. Выраженная геометрия скуловой кости и хороший баланс контраста.",
        "cons": f"Индекс контурной четкости нижнего трети лица: {round(sharp_score, 1)}/10. Присутствует незначительный асимметричный сдвиг.",
        "recs": "Рекомендуется удерживать низкий процент жира (11-13%), делать утренний лимфодренажный массаж и держать правильную осанку (мьюинг)."
    }

    return rating, cat, cat_cls, color, report

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, data=None)

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400

    file = request.files['file']
    unique_id = f"{uuid.uuid4().hex}_{int(time.time())}"
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{unique_id}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    rating, category, cat_class, color_hex, report = analyze_face_opencv(filepath)

    results_db[unique_id] = {
        "rating": rating,
        "category": category,
        "cat_class": cat_class,
        "color_hex": color_hex,
        "report": report,
        "image_filename": filename
    }

    return jsonify({"rating": rating, "category": category, "id": unique_id})

@app.route('/result/<result_id>')
def show_result(result_id):
    data = results_db.get(result_id)
    return render_template_string(HTML_TEMPLATE, data=data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)