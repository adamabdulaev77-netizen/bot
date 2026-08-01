# ==============================================================================
# 🌐 AESTHETIC AI AGENT — FLASK WEB APP & OPENCV ENGINE
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

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Aesthetic Vision AI Agent</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #050508;
            --accent-purple: #8b5cf6;
            --accent-pink: #ec4899;
            --glass-border: rgba(255, 255, 255, 0.08);
            --glass-card: rgba(18, 18, 26, 0.75);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
        body { background: var(--bg-base); color: #ffffff; min-height: 100vh; display: flex; align-items: center; justify-content: center; overflow-x: hidden; padding: 16px 12px; }
        
        #particles-canvas, #confetti-canvas { position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }
        #particles-canvas { z-index: 0; }
        #confetti-canvas { z-index: 100; }

        .app-container {
            position: relative; z-index: 10; width: 100%; max-width: 500px;
            background: var(--glass-card); backdrop-filter: blur(30px);
            border: 1px solid var(--glass-border); border-radius: 32px; padding: 25px 18px;
            box-shadow: 0 30px 70px rgba(0, 0, 0, 0.8);
        }
        .header { text-align: center; margin-bottom: 20px; }
        .header h1 { font-size: 1.8rem; font-weight: 900; background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header p { font-size: 0.85rem; color: rgba(255, 255, 255, 0.5); margin-top: 4px; }

        .upload-zone {
            border: 2px dashed rgba(255, 255, 255, 0.18); border-radius: 24px; padding: 35px 20px;
            text-align: center; cursor: pointer; transition: all 0.3s; background: rgba(255, 255, 255, 0.015);
        }
        .upload-zone:hover { border-color: var(--accent-purple); background: rgba(139, 92, 246, 0.06); }
        .btn-select { display: inline-block; background: linear-gradient(135deg, #8b5cf6, #7c3aed); color: #fff; padding: 12px 28px; border-radius: 14px; font-weight: 700; font-size: 0.9rem; margin-top: 15px; }
        #fileInput { display: none; }

        .loading-state { display: none; text-align: center; padding: 30px 10px; }
        .spinner { width: 45px; height: 45px; border: 4px solid rgba(255,255,255,0.1); border-left-color: var(--accent-purple); border-radius: 50%; margin: 0 auto 15px; animation: spin 0.9s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* Результаты */
        .result-screen { display: none; flex-direction: column; align-items: center; gap: 20px; }
        .preview-container { width: 100%; max-height: 250px; border-radius: 20px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1); }
        .preview-container img { width: 100%; height: 100%; object-fit: cover; display: block; }

        .score-gauge { position: relative; width: 170px; height: 170px; }
        .score-gauge svg { width: 100%; height: 100%; transform: rotate(-90deg); }
        .gauge-bg { fill: none; stroke: rgba(255, 255, 255, 0.05); stroke-width: 14; }
        .gauge-bar { fill: none; stroke-width: 14; stroke-linecap: round; stroke-dasharray: 565.48; stroke-dashoffset: 565.48; transition: stroke-dashoffset 1.8s cubic-bezier(0.16, 1, 0.3, 1); }
        .gauge-content { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; }
        .score-num { font-size: 3.2rem; font-weight: 900; line-height: 1; }
        .score-sub { font-size: 0.8rem; color: rgba(255, 255, 255, 0.4); font-weight: 700; }

        .category-pill { padding: 10px 26px; border-radius: 100px; font-size: 1.3rem; font-weight: 900; letter-spacing: 2px; text-transform: uppercase; border: 1px solid rgba(255, 255, 255, 0.2); }
        .cat-SUB3 { color: #ff4d4d; border-color: #ff4d4d; }
        .cat-SUB5 { color: #ff944d; border-color: #ff944d; }
        .cat-LTN  { color: #ffd11a; border-color: #ffd11a; }
        .cat-MTN  { color: #a6ff1a; border-color: #a6ff1a; }
        .cat-HTN  { color: #2eb82e; border-color: #2eb82e; }
        .cat-CHAD { color: #00ccff; border-color: #00ccff; }
        .cat-TRUE_ADAM { color: #ffd700; border-color: #ffd700; background: rgba(255,215,0,0.25); }

        /* Карточки ИИ-аналитики */
        .ai-analysis-box { width: 100%; display: flex; flex-direction: column; gap: 12px; }
        .ai-card { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 16px; padding: 14px 16px; text-align: left; }
        .ai-card-title { font-size: 0.9rem; font-weight: 800; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }
        .ai-card-text { font-size: 0.82rem; color: rgba(255,255,255,0.75); line-height: 1.45; }

        .title-pros { color: #4ade80; }
        .title-cons { color: #f87171; }
        .title-recs { color: #38bdf8; }

        .btn-restart { width: 100%; background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.12); color: #fff; padding: 12px; border-radius: 14px; font-weight: 800; cursor: pointer; }
    </style>
</head>
<body>
    <canvas id="particles-canvas"></canvas>
    <canvas id="confetti-canvas"></canvas>

    <div class="app-container">
        <div class="header">
            <h1>Aesthetic AI Agent</h1>
            <p>Строгий честный разбор внешности и геометрии</p>
        </div>

        {% if not data %}
        <div class="upload-zone" id="uploadZone" onclick="document.getElementById('fileInput').click()">
            <div style="font-size: 2.5rem; margin-bottom: 8px;">📸</div>
            <div style="font-size: 1.1rem; font-weight: 800;">Загрузи свое фото</div>
            <div style="font-size: 0.8rem; color: rgba(255,255,255,0.45); margin-top: 4px;">Выбери портрет или селфи</div>
            <div class="btn-select">Загрузить снимок</div>
            <input type="file" id="fileInput" accept="image/*" onchange="processFileUpload(this)">
        </div>

        <div class="loading-state" id="loadingState">
            <div class="spinner"></div>
            <div style="font-size: 0.9rem; font-weight: 700;">ИИ сканирует геометрию и векторы лица...</div>
        </div>
        {% endif %}

        <div class="result-screen" id="resultScreen" style="{% if data %}display:flex;{% endif %}">
            <div class="preview-container">
                <img id="resImage" src="{% if data %}/static/uploads/{{ data.image_filename }}{% endif %}" alt="Scan">
            </div>

            <div class="score-gauge">
                <svg viewBox="0 0 200 200">
                    <circle class="gauge-bg" cx="100" cy="100" r="90"></circle>
                    <circle class="gauge-bar" id="gaugeBar" cx="100" cy="100" r="90"></circle>
                </svg>
                <div class="gauge-content">
                    <div class="score-num">{% if data %}{{ data.rating }}{% else %}0{% endif %}</div>
                    <div class="score-sub">из 10 баллов</div>
                </div>
            </div>

            <div class="category-pill {% if data %}{{ data.cat_class }}{% endif %}">
                {% if data %}{{ data.category }}{% endif %}
            </div>

            {% if data %}
            <!-- РАЗБОР ОТ ИИ АГЕНТА -->
            <div class="ai-analysis-box">
                <div class="ai-card">
                    <div class="ai-card-title title-pros">🔥 Сильные стороны (Достоинства)</div>
                    <div class="ai-card-text">{{ data.report.pros }}</div>
                </div>

                <div class="ai-card">
                    <div class="ai-card-title title-cons">❌ Слабые места (Недостатки)</div>
                    <div class="ai-card-text">{{ data.report.cons }}</div>
                </div>

                <div class="ai-card">
                    <div class="ai-card-title title-recs">💡 Советы по Луксмаксингу</div>
                    <div class="ai-card-text">{{ data.report.recs }}</div>
                </div>
            </div>
            {% endif %}

            <button class="btn-restart" onclick="location.href='/'">🔄 Сканировать другое фото</button>
        </div>
    </div>

    <script>
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
        }

        // Фоновые частицы
        const pCanvas = document.getElementById('particles-canvas');
        const pCtx = pCanvas.getContext('2d');
        let particles = [];
        function resizeP() { pCanvas.width = window.innerWidth; pCanvas.height = window.innerHeight; }
        window.addEventListener('resize', resizeP); resizeP();
        class Particle {
            constructor() {
                this.x = Math.random() * pCanvas.width; this.y = Math.random() * pCanvas.height;
                this.size = Math.random() * 2 + 0.5; this.speedX = (Math.random() - 0.5) * 0.3; this.speedY = (Math.random() - 0.5) * 0.3;
                this.opacity = Math.random() * 0.5 + 0.2;
            }
            update() { this.x += this.speedX; this.y += this.speedY; if (this.x < 0) this.x = pCanvas.width; if (this.x > pCanvas.width) this.x = 0; if (this.y < 0) this.y = pCanvas.height; if (this.y > pCanvas.height) this.y = 0; }
            draw() { pCtx.fillStyle = `rgba(192, 132, 252, ${this.opacity})`; pCtx.beginPath(); pCtx.arc(this.x, this.y, this.size, 0, Math.PI * 2); pCtx.fill(); }
        }
        for (let i = 0; i < 50; i++) particles.push(new Particle());
        function animP() { pCtx.clearRect(0, 0, pCanvas.width, pCanvas.height); particles.forEach(p => { p.update(); p.draw(); }); requestAnimationFrame(animP); }
        animP();

        async function processFileUpload(input) {
            if (!input.files || !input.files[0]) return;
            document.getElementById('uploadZone').style.display = 'none';
            document.getElementById('loadingState').style.display = 'block';
            const formData = new FormData(); formData.append('file', input.files[0]);
            try {
                const response = await fetch('/analyze', { method: 'POST', body: formData });
                const result = await response.json();
                if (result.id) window.location.href = '/result/' + result.id;
            } catch (err) { alert('Ошибка загрузки!'); location.reload(); }
        }

        {% if data %}
        const rating = {{ data.rating }};
        const gaugeBar = document.getElementById('gaugeBar');
        gaugeBar.style.stroke = "{{ data.color_hex }}";
        const offset = (2 * Math.PI * 90) - (rating / 10) * (2 * Math.PI * 90);
        setTimeout(() => { gaugeBar.style.strokeDashoffset = offset; }, 150);
        {% endif %}
    </script>
</body>
</html>
"""

def generate_ai_report(rating, sym_pct, sharp_val, harm_val):
    # Генерируем суровый честный разбор
    if rating >= 8:
        pros = f"Отличная симметрия лица ({sym_pct}%). Четкая линия челюсти и скул. Оптимальная контрастность и выразительность взгляда."
        cons = "Минорные недочеты в равномерности освещения кадра."
        recs = "Поддерживай низкий процент жира в организме (10-12%), делай упор на осанку и уход за кожей."
    elif rating >= 6:
        pros = f"Хорошая базовая структура лица. Симметрия овала находится на уровне {sym_pct}%."
        cons = "Недостаточная резкость контуров нижнего трети лица. Сглаженный контраст тона кожи."
        recs = "Оптимизируй диету для снижения отечности, добавь регулярный дефаттинг (снижение жира) и уход за кожей лица."
    else:
        pros = f"Удовлетворительный баланс тона кадра ({harm_val}/10)."
        cons = f"Заметный асимметричный дисбаланс ({sym_pct}%). Низкая резкость кадра и размытые контурные линии."
        recs = "Снижай общий процент жира, начни мевинг, исправь осанку и смени стрижку под форму черепа."

    return {"pros": pros, "cons": cons, "recs": recs}

def analyze_opencv(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return 5, "LTN", "cat-LTN", "#ffd11a", {}

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

    sym_pct = round(max(35.0, min(99.0, 100.0 - (np.mean(diff) * 0.85))), 1)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    sharp_val = round(min(10.0, max(1.0, math.log1p(laplacian_var) * 1.45)), 1)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    harm_val = round(min(10.0, max(1.0, (np.mean(hsv[:, :, 1]) / 25.5) * 0.5 + (np.mean(hsv[:, :, 2]) / 25.5) * 0.5)), 1)

    raw_score = ((sym_pct / 10.0) * 0.5) + (sharp_val * 0.3) + (harm_val * 0.2)
    rating = int(np.clip(round(raw_score), 1, 10))

    cats = {
        1: ("SUB 3", "cat-SUB3", "#ff4d4d"), 2: ("SUB 3", "cat-SUB3", "#ff4d4d"),
        3: ("SUB 5", "cat-SUB5", "#ff944d"), 4: ("SUB 5", "cat-SUB5", "#ff944d"),
        5: ("LTN", "cat-LTN", "#ffd11a"), 6: ("MTN", "cat-MTN", "#a6ff1a"),
        7: ("HTN", "cat-HTN", "#2eb82e"), 8: ("CHAD", "cat-CHAD", "#00ccff"),
        9: ("CHAD", "cat-CHAD", "#00ccff"), 10: ("TRUE ADAM", "cat-TRUE_ADAM", "#ffd700")
    }

    category, cat_class, color_hex = cats.get(rating, ("LTN", "cat-LTN", "#ffd11a"))
    report = generate_ai_report(rating, sym_pct, sharp_val, harm_val)

    return rating, category, cat_class, color_hex, report

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, data=None)

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files: return jsonify({"error": "No file"}), 400
    file = request.files['file']
    unique_id = f"{uuid.uuid4().hex}_{int(time.time())}"
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{unique_id}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    rating, category, cat_class, color_hex, report = analyze_opencv(filepath)

    results_db[unique_id] = {
        "rating": rating, "category": category, "cat_class": cat_class,
        "color_hex": color_hex, "report": report, "image_filename": filename
    }
    return jsonify({"rating": rating, "category": category, "id": unique_id})

@app.route('/result/<result_id>')
def show_result(result_id):
    data = results_db.get(result_id)
    return render_template_string(HTML_TEMPLATE, data=data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)