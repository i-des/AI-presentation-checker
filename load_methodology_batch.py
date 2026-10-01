#!/usr/bin/env python3
import json
import base64
import requests
from pathlib import Path
import time

LM_STUDIO_URL = "http://127.0.0.1:1234/api/v1/chat"
MODEL = "qwen/qwen3.6-35b-a3b"
MAIN_RULES_FILE = "rules/main_rules.json"

# ✅ КОНСТАНТЫ
MAX_OUTPUT_TOKENS = 10000
EXPECTED_IMAGES_PER_CHAPTER = {
    "1": 0, "2": 33, "3": 0,
    "3.1": 7, "3.2": 7, "3.3": 7,
    "3.4": 10, "3.5": 9, "3.6": 3,
    "3.7": 5, "3.8": 1, "3.9": 1,
    "4.0": 0, "5.0": 7, "6.0": 12, "7.0": 0
}

def load_json_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def encode_image_to_base64(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def get_image_mime_type(image_path):
    ext = Path(image_path).suffix.lower()
    types = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.webp': 'image/webp'}
    return types.get(ext, 'image/png')

def send_batch_to_lm_studio(input_array, batch_num=None, previous_response_id=None, max_output_tokens=None):
    """Отправляет батч в LM Studio с поддержкой stateful API"""

    if batch_num:
        print(f"\n🚀 Отправляю батч {batch_num}...")
    else:
        print(f"\n🚀 Отправляю запрос...")

    payload = {
        "model": MODEL,
        "input": input_array,
        "max_output_tokens": max_output_tokens or MAX_OUTPUT_TOKENS
    }

    # ✅ КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Stateful API требует previous_response_id
    if previous_response_id:
        payload["previous_response_id"] = previous_response_id

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(LM_STUDIO_URL, json=payload, headers=headers, timeout=300)

        if response.status_code == 200:
            result = response.json()
            # Сохраняем response_id для следующего батча
            new_response_id = result.get("response_id")

            output = result.get('output', [])
            for item in output:
                if item.get('type') == 'message':
                    content = item.get('content', '').lower()
                    if "не вижу" in content or "не вижу изображение" in content:
                        print(f"⚠️  Модель не видит изображения в этом батче!")
                        return new_response_id
                    elif any(word in content for word in ['видел', 'увидел', 'цвет', 'белый', 'черный', 'фон']):
                        print(f"✅ Модель видит изображения! Батч обработан.")
                        return new_response_id
            print(f"✅ Батч обработан")
            return new_response_id
        else:
            print(f"❌ Ошибка! Статус: {response.status_code}")
            print(f"Ответ: {response.text[:200]}")
            return None

    except Exception as e:
        print(f"❌ Ошибка при отправке: {e}")
        return None

def verify_model_memory(final_response_id):
    """Проверяет память модели, оставаясь в том же stateful потоке"""
    print("\n🔍 ПРОВЕРКА ПАМЯТИ МОДЕЛИ (тот же поток чата)...")

    payload = {
        "model": MODEL,
        "input": """Проверь свою память по загруженной методичке Slidy:
1. Сколько изображений должно быть в главе 3.2 (Иконки)?
2. Что отображается на слайде до генерации элемента «Перегенерируемая иконка»?
3. Какие действия разрешены с иконками, а какие запрещены?
4. В главе 6.0 сколько изображений должно быть загружено?
Ответь кратко, опираясь только на загруженные правила.""",
        "previous_response_id": final_response_id,
        "max_output_tokens": 2000
    }

    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(LM_STUDIO_URL, json=payload, headers=headers, timeout=60)
        if response.status_code == 200:
            result = response.json()
            answer = result.get('output', [{}])[0].get('content', 'Нет ответа')
            print(f"\n✅ ОТВЕТ МОДЕЛИ:\n{answer}")
        else:
            print(f"❌ Ошибка проверки: {response.status_code}")
            print(f"Ответ: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Ошибка сети: {e}")

def load_methodology():
    print("🎯 ЗАГРУЗКА МЕТОДИЧКИ В LM STUDIO (stateful API)\n")

    try:
        main_rules = load_json_file(MAIN_RULES_FILE)
    except FileNotFoundError:
        print(f"❌ Файл {MAIN_RULES_FILE} не найден!")
        return

    rules_base = Path(MAIN_RULES_FILE).parent
    batch_num = 1
    previous_response_id = None  # ✅ Stateful API: начинаем с None

    # ✅ ПЕРВЫЙ БАТЧ - Приветствие
    print(f"\n📌 БАТЧ 1: Приветствие и инструкции")
    input_array = [
        {
            "type": "text",
            "content": """Я вам загружаю полную методичку по дизайну презентаций Slidy.

Вы эксперт по дизайну презентаций. Ваша задача - проверять слайды на соответствие правилам.

Далее я буду отправлять вам правила в отдельных сообщениях с примерами изображений.

Обратите внимание, что вы будете получать информацию порционно. 1 глава, текстовый файл и изображения, если есть. В каждом текстовом файле есть описание (description) к каждому изобранию, приложенному к этой главе, чтобы вы смогли точно их сопоставить.

Также обратите внимание на то, что в каждой главе есть разные изображения, где-то хорошие примеры "good_examples", где-то плохие "bad_examples", где-то контекстные пример "context_images", где-то примеры шаблонов "default_sample". Вам их нужно анализировать в зависимости от контекста.

Запомните эту информацию и подтвердите, что вы готовы."""
        }
    ]

    previous_response_id = send_batch_to_lm_studio(input_array, batch_num, previous_response_id, MAX_OUTPUT_TOKENS)
    batch_num += 1
    time.sleep(2)

    # ✅ ОСТАЛЬНЫЕ БАТЧИ - Каждая глава отдельно
    for chapter_path in main_rules.get('chapters', []):
        json_file = rules_base / chapter_path

        if not json_file.exists():
            print(f"⚠️  Не найден: {json_file}")
            continue

        print(f"\n📌 БАТЧ {batch_num}: {chapter_path}")

        try:
            rules_data = load_json_file(json_file)
            chapter_id = rules_data.get('chapter_id', '')
            norm_id = chapter_id.replace("chapter_", "").strip()
            expected_imgs = EXPECTED_IMAGES_PER_CHAPTER.get(norm_id, 0)

            input_array = [
                {
                    "type": "text",
                    "content": f"ГЛАВА {rules_data.get('chapter_id', norm_id)}: {rules_data.get('chapter_title', '')}\n\n"
                }
            ]

            for rule in rules_data.get('rules', []):
                input_array.append({
                    "type": "text",
                    "content": f"📌 ПРАВИЛО {rule['id']}: {rule['title']}\n{rule['content']}\n"
                })

            # ✅ 1. КОНТЕКСТНЫЕ ИЗОБРАЖЕНИЯ
            if 'context_images' in rules_data and rules_data['context_images']:
                input_array.append({"type": "text", "content": "\n🖼️ КОНТЕКСТНЫЕ ИЗОБРАЖЕНИЯ:\n"})
                for ctx_img in rules_data['context_images']:
                    img_path = json_file.parent / ctx_img['path']
                    if img_path.exists():
                        try:
                            base64_img = encode_image_to_base64(str(img_path))
                            mime_type = get_image_mime_type(str(img_path))
                            input_array.append({
                                "type": "image",
                                "data_url": f"data:{mime_type};base64,{base64_img}"
                            })
                            input_array.append({
                                "type": "text",
                                "content": f"[Контекст] {ctx_img['description']}\n"
                            })
                        except Exception as e:
                            print(f"    ❌ Ошибка контекстного изображения: {e}")

            # ✅ 2. DEFAULT TEMPLATE
            if 'default_template' in rules_data:
                default_template = rules_data['default_template']
                input_array.append({
                    "type": "text",
                    "content": f"\n📚 СТАНДАРТНАЯ СТРУКТУРА ШАБЛОНА:\n{default_template.get('description', '')}\n"
                })

                slides_dir = json_file.parent / "default_sample"
                for slide_key in sorted(default_template.get('slides', {}).keys()):
                    slide_info = default_template['slides'][slide_key]
                    img_relative_path = slide_info['path']
                    img_filename = Path(img_relative_path).name
                    img_path = slides_dir / img_filename

                    if img_path.exists():
                        try:
                            base64_img = encode_image_to_base64(str(img_path))
                            mime_type = get_image_mime_type(str(img_path))
                            input_array.append({
                                "type": "image",
                                "data_url": f"data:{mime_type};base64,{base64_img}"
                            })
                            input_array.append({
                                "type": "text",
                                "content": f"[Слайд {slide_key}] {slide_info['description']}\n"
                            })
                        except Exception as e:
                            print(f"    ❌ Ошибка загрузки слайда: {e}")

            # ✅ 3. DEFAULT SAMPLE
            if 'default_sample' in rules_data and 'default_template' not in rules_data:
                sample = rules_data['default_sample']
                img_dir = json_file.parent / "img"
                img_path = img_dir / Path(sample['path']).name

                if img_path.exists():
                    try:
                        base64_img = encode_image_to_base64(str(img_path))
                        mime_type = get_image_mime_type(str(img_path))
                        input_array.append({
                            "type": "image",
                            "data_url": f"data:{mime_type};base64,{base64_img}"
                        })
                        input_array.append({
                            "type": "text",
                            "content": f"[СТАНДАРТНЫЙ ПРИМЕР] {sample['description']}\n"
                        })
                    except Exception as e:
                        print(f"  ❌ Ошибка: {e}")

            # ✅ 4. GOOD/BAD EXAMPLES
            for example_type, emoji in [('good_examples', '✅'), ('bad_examples', '❌')]:
                if example_type in rules_data and rules_data[example_type]:
                    input_array.append({
                        "type": "text",
                        "content": f"\n{emoji} {'ХОРОШИЕ' if 'good' in example_type else 'ПЛОХИЕ'} ПРИМЕРЫ:\n"
                    })

                    img_dir = json_file.parent / "img"
                    for example in rules_data[example_type]:
                        img_path = img_dir / Path(example['image']).name
                        if img_path.exists():
                            try:
                                base64_img = encode_image_to_base64(str(img_path))
                                mime_type = get_image_mime_type(str(img_path))
                                input_array.append({
                                    "type": "image",
                                    "data_url": f"data:{mime_type};base64,{base64_img}"
                                })
                                input_array.append({
                                    "type": "text",
                                    "content": f"[{emoji} Пример] {example['reason']}\n"
                                })
                            except Exception as e:
                                print(f"  ❌ Ошибка: {e}")

            actual_imgs = sum(1 for x in input_array if x['type'] == 'image')
            text_items = sum(1 for x in input_array if x['type'] == 'text')
            print(f"  📊 Текст: {text_items}, Изображений: {actual_imgs}")

            # ✅ ТОЧНАЯ ВАЛИДАЦИЯ
            if expected_imgs > 0 and actual_imgs != expected_imgs:
                print(f"  ⚠️  РАСХОЖДЕНИЕ: для '{norm_id}' ожидалось {expected_imgs}, отправлено {actual_imgs}")
            elif expected_imgs == 0 and actual_imgs > 0:
                print(f"  ℹ️  Для '{norm_id}' ожидалось 0 изображений, но найдено {actual_imgs}. Это допустимо, если в JSON есть картинки.")

            # ✅ Отправляем с previous_response_id (stateful API)
            previous_response_id = send_batch_to_lm_studio(input_array, batch_num, previous_response_id, MAX_OUTPUT_TOKENS)
            batch_num += 1
            time.sleep(2)

        except Exception as e:
            print(f"❌ Ошибка при обработке {json_file}: {e}")

    # ✅ ФИНАЛЬНЫЙ БАТЧ
    print(f"\n📌 БАТЧ {batch_num}: Завершение")
    input_array = [
        {
            "type": "text",
            "content": "Конец методички. Теперь вы готовы проверять презентации по этим правилам. Подтвердите, что вы запомнили все правила."
        }
    ]
    final_response_id = send_batch_to_lm_studio(input_array, batch_num, previous_response_id, MAX_OUTPUT_TOKENS)

    if final_response_id:
        Path("last_response_id.txt").write_text(
            final_response_id,
            encoding="utf-8"
        )
        print("💾 Финальный response_id сохранён в last_response_id.txt")
    else:
        print("❌ Финальный response_id не получен. Проверьте ошибки выше.")

    # ✅ ЗАПУСК ПРОВЕРКИ ПАМЯТИ (в том же stateful потоке)
    if final_response_id:
        verify_model_memory(final_response_id)

    print("\n" + "="*80)
    print("✅ МЕТОДИЧКА ПОЛНОСТЬЮ ЗАГРУЖЕНА!")
    print("="*80)

if __name__ == "__main__":
    load_methodology()
