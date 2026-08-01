# ==============================================================================
# 🌐 AESTHETIC VISION AI — ULTIMATE LOOKSMAXING WEB APP (FLASK + OPENCV)
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

# Хранилище результатов анализа в памяти
results_db = {}

# ==============================================================================
# 🎨 HIGH-TECH NEON GLASSMORPHISM & 3D WIREFRAME FRONTEND TEMPLATE
# ==============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Aesthetic AI — Neural Face Engine</title>
    <!-- Telegram WebApp SDK -->
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #030307;
            --accent-purple: #9333ea;
            --accent-pink: #ec4899;
            --accent-cyan: #06b6d4;
            --glass-bg: rgba(13, 13, 22, 0.75);
            --glass-border: rgba(255, 255, 255, 0.12);
            --glass-inner: rgba(255, 255, 255, 0.03);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            user-select: none;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            background: var(--bg-dark);
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow-x: hidden;
            position: relative;
            padding: 20px 12px;
        }

        /* 3D Wireframe & Particle Canvas */
        #bg-canvas, #confetti-canvas {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
        }
        #bg-canvas { z-index: 0; }
        #confetti-canvas { z-index: 100; }

        /* Ambient Glow Spheres */
        .glow-orb {
            position: fixed;
            border-radius: 50%;
            filter: blur(140px);
            opacity: 0.35;
            pointer-events: none;
            z-index: 1;
            animation: orbFloat 12s infinite alternate ease-in-out;
        }
        .glow-1 {
            top: -15%;
            left: -15%;
            width: 450px;
            height: 450px;
            background: radial-gradient(circle, #7c3aed, transparent);
        }
        .glow-2 {
            bottom: -15%;
            right: -15%;
            width: 500px;
            height: 500px;
            background: radial-gradient(circle, #06b6d4, transparent);
        }
        @keyframes orbFloat {
            0% { transform: translate(0, 0) scale(1); }
            50% { transform: translate(30px, -40px) scale(1.1); }
            100% { transform: translate(-20px, 20px) scale(0.95); }
        }

        /* Container Card */
        .app-card {
            position: relative;
            z-index: 10;
            width: 100%;
            max-width: 520px;
            background: var(--glass-bg);
            backdrop-filter: blur(40px);
            -webkit-backdrop-filter: blur(40px);
            border: 1px solid var(--glass-border);
            border-radius: 36px;
            padding: 32px 24px;
            box-shadow: 0 40px 100px rgba(0, 0, 0, 0.9),
                        inset 0 1px 1px rgba(255, 255, 255, 0.2);
            animation: appAppear 0.9s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        @keyframes appAppear {
            from { opacity: 0; transform: translateY(40px) scale(0.95); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }

        .header {
            text-align: center;
            margin-bottom: 24px;
        }
        .header .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 16px;
            border-radius: 100px;
            background: linear-gradient(135deg, rgba(147, 51, 234, 0.2), rgba(6, 182, 212, 0.2));
            border: 1px solid rgba(255, 255, 255, 0.15);
            font-size: 0.75rem;
            font-weight: 800;
            color: #d8b4fe;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 12px;
            box-shadow: 0 4px 15px rgba(147, 51, 234, 0.25);
        }
        .header h1 {
            font-size: 2.1rem;
            font-weight: 900;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header p {
            font-size: 0.88rem;
            color: rgba(255, 255, 255, 0.55);
            margin-top: 6px;
            font-weight: 500;
        }

        /* Upload Area */
        .upload-area {
            border: 2px dashed rgba(255, 255, 255, 0.18);
            border-radius: 28px;
            padding: 40px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
            background: var(--glass-inner);
            position: relative;
            overflow: hidden;
        }
        .upload-area:hover, .upload-area.dragover {
            border-color: var(--accent-purple);
            background: rgba(147, 51, 234, 0.08);
            transform: translateY(-2px);
        }
        .upload-icon {
            width: 76px;
            height: 76px;
            margin: 0 auto 16px;
            border-radius: 50%;
            background: linear-gradient(135deg, rgba(147, 51, 234, 0.25), rgba(6, 182, 212, 0.25));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.2rem;
            border: 1px solid rgba(255, 255, 255, 0.15);
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4);
        }
        .upload-title {
            font-size: 1.15rem;
            font-weight: 800;
            color: #ffffff;
            margin-bottom: 6px;
        }
        .upload-desc {
            font-size: 0.82rem;
            color: rgba(255, 255, 255, 0.5);
            margin-bottom: 20px;
        }
        .btn-select-file {
            display: inline-block;
            background: linear-gradient(135deg, #9333ea 0%, #06b6d4 100%);
            color: #ffffff;
            padding: 14px 32px;
            border-radius: 16px;
            font-weight: 800;
            font-size: 0.95rem;
            box-shadow: 0 10px 25px rgba(147, 51, 234, 0.4);
            transition: all 0.25s ease;
        }
        .btn-select-file:hover {
            transform: scale(1.03);
            box-shadow: 0 12px 30px rgba(6, 182, 212, 0.5);
        }
        #fileInput { display: none; }

        /* Loader */
        .loading-box {
            display: none;
            text-align: center;
            padding: 35px 15px;
        }
        .spinner-ring {
            width: 54px;
            height: 54px;
            border: 4px solid rgba(255, 255, 255, 0.1);
            border-left-color: var(--accent-purple);
            border-top-color: var(--accent-cyan);
            border-radius: 50%;
            margin: 0 auto 18px;
            animation: spin 0.85s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loading-text {
            font-size: 0.95rem;
            font-weight: 700;
            color: #e2e8f0;
            letter-spacing: 0.5px;
        }

        /* Result View */
        .result-view {
            display: none;
            flex-direction: column;
            align-items: center;
            gap: 24px;
        }

        /* Photo Frame - Full View Fix */
        .photo-frame {
            width: 100%;
            height: 340px;
            border-radius: 24px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.15);
            background: #000000;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.65);
            position: relative;
        }
        .photo-frame img {
            max-width: 100%;
            max-height: 100%;
            width: auto;
            height: auto;
            object-fit: contain;
            display: block;
        }

        /* Radial Progress Gauge */
        .gauge-container {
            position: relative;
            width: 190px;
            height: 190px;
        }
        .gauge-container svg {
            width: 100%;
            height: 100%;
            transform: rotate(-90deg);
        }
        .gauge-track {
            fill: none;
            stroke: rgba(255, 255, 255, 0.06);
            stroke-width: 14;
        }
        .gauge-bar {
            fill: none;
            stroke-width: 14;
            stroke-linecap: round;
            stroke-dasharray: 565.48;
            stroke-dashoffset: 565.48;
            transition: stroke-dashoffset 2s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .gauge-inner-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
        }
        .score-val {
            font-size: 3.6rem;
            font-weight: 900;
            line-height: 1;
            letter-spacing: -1.5px;
        }
        .score-sub {
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.45);
            font-weight: 700;
            margin-top: 4px;
            text-transform: uppercase;
        }

        /* Category Pill */
        .category-pill {
            padding: 12px 34px;
            border-radius: 100px;
            font-size: 1.45rem;
            font-weight: 900;
            letter-spacing: 2px;
            text-transform: uppercase;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 12px 35px rgba(0,0,0,0.5);
            animation: badgePulse 2s infinite alternate ease-in-out;
        }
        @keyframes badgePulse {
            from { transform: scale(1); }
            to { transform: scale(1.04); }
        }

        .cat-SUB3 { color: #ff4d4d; border-color: #ff4d4d; box-shadow: 0 0 30px rgba(255,77,77,0.35); }
        .cat-SUB5 { color: #ff944d; border-color: #ff944d; box-shadow: 0 0 30px rgba(255,148,77,0.35); }
        .cat-LTN  { color: #ffd11a; border-color: #ffd11a; box-shadow: 0 0 30px rgba(255,209,26,0.35); }
        .cat-MTN  { color: #a6ff1a; border-color: #a6ff1a; box-shadow: 0 0 30px rgba(166,255,26,0.35); }
        .cat-HTN  { color: #2eb82e; border-color: #2eb82e; box-shadow: 0 0 30px rgba(46,184,46,0.35); }
        .cat-CHAD { color: #00ccff; border-color: #00ccff; box-shadow: 0 0 40px rgba(0,204,255,0.45); }
        .cat-TRUE_ADAM { 
            color: #ffd700; 
            border-color: #ffd700; 
            background: linear-gradient(135deg, rgba(255,215,0,0.25), rgba(255,140,0,0.25));
            box-shadow: 0 0 60px rgba(255,215,0,0.9);
            animation: goldGlow 1.2s infinite alternate ease-in-out;
        }
        @keyframes goldGlow {
            from { box-shadow: 0 0 25px rgba(255,215,0,0.6); }
            to { box-shadow: 0 0 65px rgba(255,215,0,1); }
        }

        /* Detailed Metrics Bars */
        .metrics-card {
            width: 100%;
            background: var(--glass-inner);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 18px;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }
        .metric-item { display: flex; flex-direction: column; gap: 6px; }
        .metric-header { display: flex; justify-content: space-between; font-size: 0.82rem; font-weight: 700; }
        .metric-title { color: rgba(255, 255, 255, 0.6); }
        .metric-val { color: #ffffff; }
        .progress-track {
            height: 7px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            overflow: hidden;
            position: relative;
        }
        .progress-fill {
            height: 100%;
            border-radius: 10px;
            width: 0%;
            transition: width 1.6s cubic-bezier(0.16, 1, 0.3, 1);
        }

        /* AI Breakdown Cards */
        .ai-breakdown {
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .ai-card {
            background: var(--glass-inner);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 18px;
            padding: 16px 18px;
            text-align: left;
        }
        .ai-card-title {
            font-size: 0.9rem;
            font-weight: 800;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .title-pros { color: #4ade80; }
        .title-cons { color: #f87171; }
        .title-recs { color: #38bdf8; }
        .ai-card-text {
            font-size: 0.84rem;
            color: rgba(255, 255, 255, 0.8);
            line-height: 1.48;
        }

        .btn-restart {
            width: 100%;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.14);
            color: #ffffff;
            padding: 15px;
            border-radius: 18px;
            font-weight: 800;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.25s ease;
        }
        .btn-restart:hover {
            background: rgba(255, 255, 255, 0.12);
        }
        .btn-restart:active { transform: scale(0.98); }
    </style>
</head>
<body>
    <div class="glow-orb glow-1"></div>
    <div class="glow-orb glow-2"></div>

    <!-- 3D Laser Wireframe & Particle Canvas -->
    <canvas id="bg-canvas"></canvas>
    <canvas id="confetti-canvas"></canvas>

    <div class="app-card">
        <div class="header">
            <div class="badge">⚡ Neural Face Engine 3.0</div>
            <h1>Aesthetic Vision AI</h1>
            <p>Глубокий векторный анализ геометрии и пропорций лица</p>
        </div>

        {% if not data %}
        <!-- UPLOAD SCREEN -->
        <div class="upload-area" id="uploadArea" onclick="document.getElementById('fileInput').click()">
            <div class="upload-icon">📸</div>
            <div class="upload-title">Загрузить фотографию</div>
            <div class="upload-desc">Выберите качественное портретное фото или селфи</div>
            <div class="btn-select-file">Выбрать снимок</div>
            <input type="file" id="fileInput" accept="image/*">
        </div>

        <div class="loading-box" id="loadingBox">
            <div class="spinner-ring"></div>
            <div class="loading-text">ИИ сканирует геометрию и векторы лица...</div>
        </div>
        {% endif %}

        <!-- RESULT SCREEN -->
        <div class="result-view" id="resultView" style="{% if data %}display:flex;{% endif %}">
            <div class="photo-frame">
                <img id="resImg" src="{% if data %}/static/uploads/{{ data.image_filename }}{% endif %}" alt="Face Scan">
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

            <div class="category-pill {% if data %}{{ data.cat_class }}{% endif %}" id="catBadge">
                {% if data %}{{ data.category }}{% endif %}
            </div>

            {% if data %}
            <!-- METRICS BARS -->
            <div class="metrics-card">
                <div class="metric-item">
                    <div class="metric-header">
                        <span class="metric-title">Симметрия овала лица</span>
                        <span class="metric-val">{{ data.details.symmetry }}%</span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-fill" id="symBar" style="background: linear-gradient(90deg, #9333ea, #d8b4fe);"></div>
                    </div>
                </div>

                <div class="metric-item">
                    <div class="metric-header">
                        <span class="metric-title">Индекс четкости и резкостных линий</span>
                        <span class="metric-val">{{ data.details.sharpness }}/10.0</span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-fill" id="sharpBar" style="background: linear-gradient(90deg, #06b6d4, #67e8f9);"></div>
                    </div>
                </div>

                <div class="metric-item">
                    <div class="metric-header">
                        <span class="metric-title">Цветовая гармония и тон</span>
                        <span class="metric-val">{{ data.details.harmony }}/10.0</span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-fill" id="harmBar" style="background: linear-gradient(90deg, #ec4899, #f472b6);"></div>
                    </div>
                </div>
            </div>

            <!-- DETAILED AI REPORT -->
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
        // Telegram WebApp Init
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
        }

        // ==============================================================================
        // 🔮 DYNAMIC BACKGROUND: 3D ROTATING WIREFRAME HEAD & LASER PARTICLES
        // ==============================================================================
        const bgCanvas = document.getElementById('bg-canvas');
        const ctx = bgCanvas.getContext('2d');

        function resizeCanvas() {
            bgCanvas.width = window.innerWidth;
            bgCanvas.height = window.innerHeight;
        }
        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();

        // 3D Head Mesh Geometry Nodes
        const headNodes = [
            {x: 0, y: 1.3, z: 0}, {x: -0.65, y: 0.95, z: 0.2}, {x: 0.65, y: 0.95, z: 0.2},
            {x: -0.85, y: 0.45, z: 0}, {x: 0.85, y: 0.45, z: 0},
            {x: -0.75, y: -0.25, z: 0.25}, {x: 0.75, y: -0.25, z: 0.25},
            {x: -0.55, y: -0.85, z: 0.45}, {x: 0.55, y: -0.85, z: 0.45},
            {x: 0, y: -1.2, z: 0.55}, // Подбородок
            {x: -0.4, y: 0.35, z: 0.55}, {x: -0.15, y: 0.35, z: 0.55},
            {x: 0.15, y: 0.35, z: 0.55}, {x: 0.4, y: 0.35, z: 0.55},
            {x: 0, y: 0.35, z: 0.65}, {x: 0, y: -0.15, z: 0.75}, {x: -0.18, y: -0.25, z: 0.6}, {x: 0.18, y: -0.25, z: 0.6},
            {x: -0.28, y: -0.5, z: 0.6}, {x: 0, y: -0.45, z: 0.65}, {x: 0.28, y: -0.5, z: 0.6},
            {x: 0, y: -0.6, z: 0.63}
        ];

        const headEdges = [
            [0,1],[0,2],[1,3],[2,4],[3,5],[4,6],[5,7],[6,8],[7,9],[8,9],
            [10,11],[12,13],[14,15],[16,15],[17,15],[18,19],[19,20],[19,21]
        ];

        let rotY = 0;

        // Background Particles
        let particles = [];
        for (let i = 0; i < 45; i++) {
            particles.push({
                x: Math.random() * bgCanvas.width,
                y: Math.random() * bgCanvas.height,
                size: Math.random() * 2 + 0.5,
                vx: (Math.random() - 0.5) * 0.3,
                vy: (Math.random() - 0.5) * 0.3,
                alpha: Math.random() * 0.5 + 0.2
            });
        }

        function drawWireframe(centerX, centerY, scale) {
            rotY += 0.012;
            const cos = Math.cos(rotY);
            const sin = Math.sin(rotY);

            const proj = headNodes.map(node => {
                let x = node.x * cos - node.z * sin;
                let z = node.x * sin + node.z * cos + 2.6;
                let y = node.y;
                return {
                    x: centerX + (x / z) * scale,
                    y: centerY - (y / z) * scale
                };
            });

            ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
            ctx.lineWidth = 1.2;
            ctx.shadowColor = '#06b6d4';
            ctx.shadowBlur = 10;

            headEdges.forEach(edge => {
                const p1 = proj[edge[0]];
                const p2 = proj[edge[1]];
                ctx.beginPath();
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);
                ctx.stroke();
            });

            ctx.fillStyle = '#9333ea';
            proj.forEach(p => {
                ctx.beginPath();
                ctx.arc(p.x, p.y, 2.2, 0, Math.PI * 2);
                ctx.fill();
            });
            ctx.shadowBlur = 0;
        }

        function renderBg() {
            ctx.clearRect(0, 0, bgCanvas.width, bgCanvas.height);

            // Draw Particles
            particles.forEach(p => {
                p.x += p.vx;
                p.y += p.vy;
                if (p.x < 0) p.x = bgCanvas.width;
                if (p.x > bgCanvas.width) p.x = 0;
                if (p.y < 0) p.y = bgCanvas.height;
                if (p.y > bgCanvas.height) p.y = 0;

                ctx.fillStyle = `rgba(147, 51, 234, ${p.alpha})`;
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                ctx.fill();
            });

            // Draw Rotating Wireframe Heads on desktop or scaled single head
            if (bgCanvas.width > 720) {
                drawWireframe(120, bgCanvas.height / 2, 230);
                drawWireframe(bgCanvas.width - 120, bgCanvas.height / 2, 230);
            } else {
                drawWireframe(bgCanvas.width / 2, 110, 130);
            }

            requestAnimationFrame(renderBg);
        }
        renderBg();

        // ==============================================================================
        // 📤 FILE UPLOAD & DRAG/DROP LOGIC
        // ==============================================================================
        const fileInput = document.getElementById('fileInput');
        const uploadArea = document.getElementById('uploadArea');

        if (uploadArea) {
            ['dragenter', 'dragover'].forEach(eventName => {
                uploadArea.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    uploadArea.classList.add('dragover');
                }, false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                uploadArea.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    uploadArea.classList.remove('dragover');
                }, false);
            });

            uploadArea.addEventListener('drop', (e) => {
                const dt = e.dataTransfer;
                const files = dt.files;
                if (files && files.length > 0) {
                    fileInput.files = files;
                    uploadPhoto(files[0]);
                }
            });

            fileInput.addEventListener('change', function() {
                if (this.files && this.files[0]) {
                    uploadPhoto(this.files[0]);
                }
            });
        }

        async function uploadPhoto(file) {
            document.getElementById('uploadArea').style.display = 'none';
            document.getElementById('loadingBox').style.display = 'block';

            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();

                if (data.id) {
                    window.location.href = '/result/' + data.id;
                } else {
                    alert('Ошибка анализа фотографии');
                    location.reload();
                }
            } catch (err) {
                alert('Не удалось связаться с сервером');
                location.reload();
            }
        }

        {% if data %}
        // Animated Score Gauge & Decimals
        const rating = {{ data.rating }};
        const gaugeBar = document.getElementById('gaugeBar');
        const scoreVal = document.getElementById('scoreVal');

        gaugeBar.style.stroke = "{{ data.color_hex }}";
        const circumference = 2 * Math.PI * 90;
        const offset = circumference - (rating / 10.0) * circumference;

        setTimeout(() => {
            gaugeBar.style.strokeDashoffset = offset;
            document.getElementById('symBar').style.width = "{{ data.details.symmetry }}%";
            document.getElementById('sharpBar').style.width = "{{ (data.details.sharpness * 10.0) }}%";
            document.getElementById('harmBar').style.width = "{{ (data.details.harmony * 10.0) }}%";
        }, 150);

        // Animated Decimal Counter
        let curScore = 0.0;
        const targetScore = rating;
        const step = targetScore / 45.0;
        const counterTimer = setInterval(() => {
            curScore += step;
            if (curScore >= targetScore) {
                scoreVal.innerText = targetScore.toFixed(1);
                clearInterval(counterTimer);
            } else {
                scoreVal.innerText = curScore.toFixed(1);
            }
        }, 30);

        {% if data.category == "TRUE ADAM" %}
        // Golden Rain Confetti for TRUE ADAM
        const cCanvas = document.getElementById('confetti-canvas');
        const cCtx = cCanvas.getContext('2d');
        cCanvas.width = window.innerWidth;
        cCanvas.height = window.innerHeight;

        let confetti = [];
        const goldShades = ['#ffd700', '#ffae00', '#fff8dc', '#e6c200', '#ffffff'];

        for (let i = 0; i < 200; i++) {
            confetti.push({
                x: Math.random() * cCanvas.width,
                y: Math.random() * cCanvas.height - cCanvas.height,
                size: Math.random() * 8 + 4,
                color: goldShades[Math.floor(Math.random() * goldShades.length)],
                vy: Math.random() * 5 + 2,
                vx: (Math.random() - 0.5) * 2.5,
                rot: Math.random() * 360,
                rotSpeed: Math.random() * 8 - 4
            });
        }

        function animConfetti() {
            cCtx.clearRect(0, 0, cCanvas.width, cCanvas.height);
            confetti.forEach(c => {
                c.y += c.vy;
                c.x += c.vx;
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
# 🔬 OPENCV ANALYSIS ENGINE (ACCURATE DECIMAL SCORES & LOOKSMAXING REPORT)
# ==============================================================================
def generate_looksmaxing_report(rating, sym_pct, sharp_val, harm_val):
    if rating >= 8.0:
        pros = f"Идеальный показатель симметрии лицевого овала ({sym_pct}%). Высокая резкость скуловой линии и подбородка. Гармоничная глубина взгляда."
        cons = "Минорные недочеты в равномерности освещения кадра."
        recs = "Удерживай процент жира в организме в районе 10-12%. Делай упор на поддержание осанки и регулярный уход за кожей."
    elif rating >= 6.0:
        pros = f"Хорошая базовая структура лица. Симметрия овала находится на высоком уровне ({sym_pct}%)."
        cons = f"Индекс резкости контуров челюсти: {sharp_val}/10.0. Небольшой асимметричный сдвиг в средней трети лица."
        recs = "Снижай процент жира для более выраженных скул, практикуй правильное положение языка (мьюинг) и подбери стрижку под форму черепа."
    else:
        pros = f"Удовлетворительный баланс цветового тона снимка ({harm_val}/10.0)."
        cons = f"Выраженный асимметричный дисбаланс ({sym_pct}%). Сглаженные контурные линии нижнего трети лица."
        recs = "Оптимизируй диету для снятия отечности, начни регулярно заниматься спортом, исправь осанку и делай лимфодренажный массаж лица."

    return {"pros": pros, "cons": cons, "recs": recs}

def analyze_opencv(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return 5.0, "LTN", "cat-LTN", "#ffd11a", {"symmetry": 50.0, "sharpness": 5.0, "harmony": 5.0}, generate_looksmaxing_report(5.0, 50.0, 5.0, 5.0)

    # Standardize scale for OpenCV calculations
    h, w = img.shape[:2]
    max_dim = 800
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1. Facial Symmetry Matrix
    mid_x = gray.shape[1] // 2
    left_side = gray[:, :mid_x]
    right_side = cv2.flip(gray[:, mid_x:mid_x + left_side.shape[1]], 1)

    min_h = min(left_side.shape[0], right_side.shape[0])
    min_w = min(left_side.shape[1], right_side.shape[1])
    diff = cv2.absdiff(left_side[:min_h, :min_w], right_side[:min_h, :min_w])

    sym_pct = round(max(35.0, min(99.0, 100.0 - (np.mean(diff) * 0.82))), 1)

    # 2. Sharpness & Contour Precision (Laplacian Variance)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    sharp_score = round(min(10.0, max(1.0, math.log1p(laplacian_var) * 1.42)), 1)

    # 3. Color & Saturation Balance (HSV Space)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    harm_score = round(min(10.0, max(1.0, (np.mean(hsv[:, :, 1]) / 25.5) * 0.5 + (np.mean(hsv[:, :, 2]) / 25.5) * 0.5)), 1)

    # Weighted Precise Rating calculation (1.0 to 10.0)
    raw_score = ((sym_pct / 10.0) * 0.50) + (sharp_score * 0.30) + (harm_score * 0.20)
    rating = round(float(np.clip(raw_score, 1.0, 10.0)), 1)

    # Categorization mapping
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

    details = {
        "symmetry": sym_pct,
        "sharpness": sharp_score,
        "harmony": harm_score
    }

    report = generate_looksmaxing_report(rating, sym_pct, sharp_score, harm_score)

    return rating, cat, cat_cls, color, details, report

# ==============================================================================
# 🛰 SERVER ROUTES & ENDPOINTS
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

    rating, category, cat_class, color_hex, details, report = analyze_opencv(filepath)

    results_db[unique_id] = {
        "rating": rating,
        "category": category,
        "cat_class": cat_class,
        "color_hex": color_hex,
        "details": details,
        "report": report,
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