import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

TEMPLATES_DIR = BASE_DIR / "templates"

LOAD_SCRIPT = BASE_DIR / "load_methodology_batch.py"
CHECK_SCRIPT = BASE_DIR / "check_presentation.py"
CSV_SCRIPT = BASE_DIR / "make_results_csv.py"

MAX_PRESENTATIONS = 2


def run_script(command):
    result = subprocess.run(
        command,
        cwd=BASE_DIR
    )

    if result.returncode != 0:
        print("\n❌ Скрипт завершился с ошибкой.")
        return False

    return True


def main():

    # ==============================
    # 1. МЕТОДИЧКА
    # ==============================

    print("\nКак поступить с методичкой?")
    print("1 — загрузить методичку заново")
    print("2 — использовать существующий response_id")

    choice = input("\nВыбери 1 или 2: ").strip()

    if choice == "1":

        print("\n📚 Загружаю методичку...")

        if not run_script([
            sys.executable,
            str(LOAD_SCRIPT)
        ]):
            return

    elif choice == "2":

        response_id = input(
            "\nВставь response_id: "
        ).strip()

        if not response_id:
            print("❌ response_id пустой.")
            return

        (BASE_DIR / "last_response_id.txt").write_text(
            response_id,
            encoding="utf-8"
        )

        print("✅ response_id сохранён.")

    else:
        print("❌ Нужно выбрать 1 или 2.")
        return


    # ==============================
    # 2. НАХОДИМ ПРЕЗЕНТАЦИИ
    # ==============================

    presentations = sorted([
        folder
        for folder in TEMPLATES_DIR.iterdir()
        if folder.is_dir()
    ])


    if not presentations:
        print("\n❌ В templates нет презентаций.")
        return


    presentations = presentations[:MAX_PRESENTATIONS]


    print("\n📂 Будут проверены:")

    for presentation in presentations:
        print(f"   • {presentation.name}")


    # ==============================
    # 3. ПРОВЕРЯЕМ ПРЕЗЕНТАЦИИ
    # ==============================

    for presentation in presentations:

        print("\n" + "=" * 60)
        print(f"🔎 Проверяю: {presentation.name}")
        print("=" * 60)

        if not run_script([
            sys.executable,
            str(CHECK_SCRIPT),
            presentation.name
        ]):
            print(
                f"⚠️ Ошибка при проверке "
                f"{presentation.name}"
            )


    # ==============================
    # 4. ОБНОВЛЯЕМ CSV
    # ==============================

    print("\n📊 Обновляю таблицу...")

    if not run_script([
        sys.executable,
        str(CSV_SCRIPT)
    ]):
        return


    print("\n🎉 Готово!")


if __name__ == "__main__":
    main()
