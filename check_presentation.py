#!/usr/bin/env python3
import json
import base64
import requests
import os
from pathlib import Path
import sys

# ⚙️ НАСТРОЙКИ
LM_STUDIO_URL = "http://127.0.0.1:1234/api/v1/chat"
MODEL = "qwen/qwen3.6-35b-a3b"
PRES_NAME = sys.argv[1]

# Пути к файлам
ID_FILE = "last_response_id.txt"  # ID чата, куда мы загрузили методичку
TEMPLATE_DIR = Path(f"templates/{PRES_NAME}")  # Папка с шаблонами
METADATA_FILE = Path(f"templates/{PRES_NAME}/metadata.json") # Файл с метаданными (предполагаю, что он там же)
REPORT_FILE = f"templates/{PRES_NAME}/{PRES_NAME}_report.txt"

def encode_image_to_base64(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def get_image_mime_type(image_path):
    ext = Path(image_path).suffix.lower()
    # Добавил support для webp
    types = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.webp': 'image/webp'}
    return types.get(ext, 'image/png')

def analyze_full_presentation():
    print("🚀 Скрипт 5: Полный анализ презентации (Один запрос: Мета + Обложка + 33 Слайда)\n")

    # 1. Читаем ID методички
    file_path = Path(ID_FILE)
    if not file_path.exists():
        print(f"❌ Ошибка: Файл {ID_FILE} не найден!")
        print("   Сначала запустите 'upload_memory_test.py' или 'load_methodology.py'.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        base_methodology_id = f.read().strip()

    print(f"🆔 Используем ID методички: {base_methodology_id}")

    # 2. Читаем Metadata
    meta_text = "Metadata не найден."
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                meta_data = json.load(f)
            title = meta_data.get('title', 'Без названия')
            palette = meta_data.get('palette', [])
            # Формируем текст для модели
            palette_str = ", ".join(palette) if isinstance(palette, list) else str(palette)
            meta_text = f"Название презентации: {title}\nЦветовая палитра: {palette_str}"
            print(f"📄 Найдены метаданные: {title}")
        except Exception as e:
            print(f"⚠️ Ошибка чтения metadata: {e}")
    else:
        print(f"⚠️ Файл {METADATA_FILE} не найден.")

    # 3. Собираем все изображения (Обложка + Слайды)
    input_array = []

    # 3.1. Добавляем текст метаданных
    input_array.append({
        "type": "text",
        "content": f"Информация о презентации:\n{meta_text}\n\n"
    })

    # 3.2. Добавляем Обложку
    cover_path = Path(f"templates/{PRES_NAME}/00_cover.webp")
    if cover_path.exists():
        print(f"🖼️ Добавляю обложку: 00_cover.webp")
        base64_img = encode_image_to_base64(str(cover_path))
        mime_type = get_image_mime_type(str(cover_path))
        input_array.append({
            "type": "image",
            "data_url": f"data:{mime_type};base64,{base64_img}"
        })
        input_array.append({
            "type": "text",
            "content": "[Обложка презентации]\n"
        })

    # 3.3. Добавляем все слайды (0.jpg ... 33.jpg)
    print(f"📂 Собираю слайды из: {TEMPLATE_DIR}")
    slides = sorted(TEMPLATE_DIR.glob("*.jpg")) + sorted(TEMPLATE_DIR.glob("*.png"))

    # Фильтруем, чтобы не взять обложку, если она вдруг в списке (хотя у неё расширение webp)
    slides = [s for s in slides if s.name != "00_cover.webp"]

    if not slides:
        print("⚠️  Слайды не найдены.")
        return

    print(f"✅ Найдено слайдов: {len(slides)}")

    for i, img_path in enumerate(slides):
        print(f"   Кодирую слайд {i+1}/{len(slides)}...")
        base64_img = encode_image_to_base64(str(img_path))
        mime_type = get_image_mime_type(str(img_path))

        # Добавляем изображение
        input_array.append({
            "type": "image",
            "data_url": f"data:{mime_type};base64,{base64_img}"
        })
        # Добавляем подпись к слайду
        input_array.append({
            "type": "text",
            "content": f"[Слайд {i+1}]\n"
        })

    # 4. Формируем жесткий запрос (Prompt)
    # Мы явно запрещаем модели придумывать правила
    prompt = """Проанализируй эту презентацию (обложка + 33 слайда) по загруженной методичке Slidy.

Опиши каждый слайд, что ты на нем видишь и дай оценку относительно всех правил, что ты узнал.
В конце презентации скажи, презентация проходит или нет.

ВАЖНО:
В самом конце ответа ОБЯЗАТЕЛЬНО добавь отдельной последней строкой один из двух вариантов:

FINAL_RESULT: PASS

или

FINAL_RESULT: FAIL

Используй только эти два варианта.
PASS означает, что презентация проходит проверку.
FAIL означает, что презентация не проходит проверку.
"""

    input_array.append({
        "type": "text",
        "content": prompt
    })

    # 5. Отправляем в LM Studio
    print("\n⏳ Отправляю полный пакет данных (обложка + метаданные + 33 слайда)...")
    print("   (Это может занять время из-за большого объема данных)")

    payload = {
        "model": MODEL,
        "input": input_array,
        "previous_response_id": base_methodology_id, # Ссылаемся на чат с методичкой
        "max_output_tokens": 200000  # Увеличил лимит ответа, так как отчет будет большим
    }

    headers = {"Content-Type": "application/json"}

    try:
        # Увеличил таймаут до 10 минут (600 сек), так как 33 картинки обрабатываются долго
        response = requests.post(LM_STUDIO_URL, json=payload, headers=headers, timeout=600)

        if response.status_code == 200:
            result = response.json()
            output = result.get('output', [])

            if output and len(output) > 0:
                analysis = output[-1].get('content', 'Нет анализа')

                # Сохраняем отчет
                report_path = Path(REPORT_FILE)
                with open(report_path, 'w', encoding='utf-8') as report_f:
                    report_f.write(f"ОТЧЕТ ПО ПОЛНОМУ АНАЛИЗУ ПРЕЗЕНТАЦИИ\n")
                    report_f.write(f"Использован ID методички: {base_methodology_id}\n\n")
                    report_f.write(analysis)

                print(f"\n✅ Анализ завершен! Отчет сохранен в: {report_path}")
            else:
                print("❌ Модель не вернула текст.")
        else:
            print(f"❌ Ошибка LM Studio: {response.status_code}")
            print(f"Ответ: {response.text[:300]}")

    except Exception as e:
        print(f"❌ Ошибка сети: {e}")

if __name__ == "__main__":
    analyze_full_presentation()
