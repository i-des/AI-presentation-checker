#!/usr/bin/env python3

import csv
from pathlib import Path


# ============================================================
# ⚙️ НАСТРОЙКИ
# ============================================================

TEMPLATES_DIR = Path("templates")

OUTPUT_CSV = Path("presentations_results.csv")


# ============================================================
# 🎯 ОПРЕДЕЛЯЕМ РЕЗУЛЬТАТ
# ============================================================

def normalize_result(text):
    """
    Превращает содержимое result.txt
    в одно из трёх значений:

    ПРОХОДИТ
    НЕ ПРОХОДИТ
    НЕ ОПРЕДЕЛЕНО
    """

    text = text.strip().upper()

    # Если в файле каким-то образом оказался
    # весь текст проверки, ищем нужные слова.

    if "НЕ ПРОХОДИТ" in text:
        return "НЕ ПРОХОДИТ"

    if "ПРОХОДИТ" in text:
        return "ПРОХОДИТ"

    # Дополнительно поддерживаем PASS / FAIL

    if "FINAL_RESULT: FAIL" in text:
        return "НЕ ПРОХОДИТ"

    if "FINAL_RESULT: PASS" in text:
        return "ПРОХОДИТ"

    return "НЕ ОПРЕДЕЛЕНО"


# ============================================================
# 📊 СОБИРАЕМ CSV
# ============================================================

def make_results_csv():

    print("📊 Создаю общую таблицу результатов...\n")

    if not TEMPLATES_DIR.exists():
        print(
            f"❌ Папка не найдена: {TEMPLATES_DIR}"
        )
        return

    rows = []

    # --------------------------------------------------------
    # Перебираем все папки презентаций
    # --------------------------------------------------------

    presentation_dirs = sorted(
        [
            folder
            for folder in TEMPLATES_DIR.iterdir()
            if folder.is_dir()
        ]
    )

    if not presentation_dirs:
        print(
            "❌ В папке templates нет "
            "папок с презентациями."
        )
        return

    for presentation_dir in presentation_dirs:

        presentation_name = presentation_dir.name

        result_file = (
            presentation_dir / f"{presentation_name}_report.txt"
        )

        print(
            f"🔍 {presentation_name}"
        )

        # ----------------------------------------------------
        # Проверяем наличие result.txt
        # ----------------------------------------------------

        if not result_file.exists():

            print(
                "   ⚠️ result.txt не найден"
            )

            result = "НЕ ПРОВЕРЯЛАСЬ"

        else:

            try:

                with open(
                    result_file,
                    "r",
                    encoding="utf-8"
                ) as f:

                    raw_result = f.read()

                result = normalize_result(
                    raw_result
                )

                print(
                    f"   → {result}"
                )

            except Exception as e:

                print(
                    f"   ❌ Ошибка чтения: {e}"
                )

                result = "ОШИБКА"

        # ----------------------------------------------------
        # Добавляем строку
        # ----------------------------------------------------

        rows.append({
            "Презентация": presentation_name,
            "Результат": result
        })

    # ========================================================
    # 💾 СОХРАНЯЕМ CSV
    # ========================================================

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "Презентация",
                "Результат"
            ]
        )

        writer.writeheader()

        writer.writerows(rows)

    # ========================================================
    # 📈 СТАТИСТИКА
    # ========================================================

    passed = sum(
        1
        for row in rows
        if row["Результат"] == "ПРОХОДИТ"
    )

    failed = sum(
        1
        for row in rows
        if row["Результат"] == "НЕ ПРОХОДИТ"
    )

    not_checked = sum(
        1
        for row in rows
        if row["Результат"] == "НЕ ПРОВЕРЯЛАСЬ"
    )

    unknown = sum(
        1
        for row in rows
        if row["Результат"] == "НЕ ОПРЕДЕЛЕНО"
    )

    errors = sum(
        1
        for row in rows
        if row["Результат"] == "ОШИБКА"
    )

    print("\n" + "=" * 50)

    print(
        f"📊 Всего презентаций: {len(rows)}"
    )

    print(
        f"✅ ПРОХОДИТ: {passed}"
    )

    print(
        f"❌ НЕ ПРОХОДИТ: {failed}"
    )

    print(
        f"⚪ НЕ ПРОВЕРЯЛАСЬ: {not_checked}"
    )

    print(
        f"❓ НЕ ОПРЕДЕЛЕНО: {unknown}"
    )

    print(
        f"⚠️ ОШИБКА: {errors}"
    )

    print("=" * 50)

    print(
        f"\n💾 CSV сохранён: {OUTPUT_CSV}"
    )


# ============================================================
# ▶️ ЗАПУСК
# ============================================================

if __name__ == "__main__":
    make_results_csv()
