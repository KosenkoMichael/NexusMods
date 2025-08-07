import os
import json
import time
import shutil
import zipfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib.parse
from typing import Dict, List, Optional


# Конфигурационные константы
MOD_NAME_TO_ID: Dict[str, int] = {
    "animation_events": 21,
    "book_finder": 121,
    "ChatBlock": 68,
    "Decode_Helper": 252,
    "NumericUI": 14,
    "PingMonitor": 13,
    "scoreboard": 22,
    "SoloPlay": 176,
    "Spidey Sense": 268,
    "true_level": 156,
}

MOD_LIST_FILE = "Z:/SteamLibrary/steamapps/common/Warhammer 40,000 DARKTIDE/mods/mod_load_order.txt"
MODS_FOLDER = "Z:/SteamLibrary/steamapps/common/Warhammer 40,000 DARKTIDE/mods"
GAME_DOMAIN = "warhammer40kdarktide"


def setup_driver(temp_folder: str) -> webdriver.Chrome:
    """Настраивает и возвращает экземпляр Chrome WebDriver."""
    options = Options()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")

    prefs = {
        "download.default_directory": temp_folder,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    options.add_experimental_option("prefs", prefs)

    return webdriver.Chrome(options=options)


def load_cookies(driver: webdriver.Chrome, cookies_file: str = "cookies.json") -> None:
    """Загружает cookies из файла в драйвер."""
    if not os.path.exists(cookies_file):
        print(f"Файл {cookies_file} не найден. Авторизация не будет выполнена.")
        return

    with open(cookies_file, "r", encoding="utf-8") as f:
        cookies = json.load(f)
        for cookie in cookies:
            cookie.pop("sameSite", None)
            cookie.pop("priority", None)
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"[Cookie Error] {e}")
    
    driver.refresh()
    time.sleep(3)


def download_mod_file(driver: webdriver.Chrome, mod_id: int) -> bool:
    """
    Выполняет скачивание мода по его ID.
    Возвращает True, если скачивание прошло успешно.
    """
    try:
        print(f"Открытие страницы мода ID {mod_id}")
        driver.get(f"https://www.nexusmods.com/{GAME_DOMAIN}/mods/{mod_id}")

        manual_link = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(translate(., 'MANUAL', 'manual'), 'manual')]")
            )
        )
        manual_url = manual_link.get_attribute("href")
        if manual_url.startswith("/"):
            manual_url = urllib.parse.urljoin("https://www.nexusmods.com", manual_url)

        driver.get(manual_url)

        slow_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "slowDownloadButton"))
        )
        slow_button.click()
        print("Slow download started")
        time.sleep(5)
        return True

    except Exception as e:
        print(f"Ошибка при скачивании мода {mod_id}: {e}")
        return False


def process_single_mod(driver: webdriver.Chrome, mod_name: str) -> None:
    """Обрабатывает один мод: скачивает и устанавливает его."""
    mod_id = MOD_NAME_TO_ID.get(mod_name)
    if not mod_id:
        print(f"Мод '{mod_name}' не отслеживается.")
        return

    print(f"Обработка мода '{mod_name}' (ID: {mod_id})")

    # Открываем новую вкладку для скачивания
    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[-1])

    if download_mod_file(driver, mod_id):
        time.sleep(5)  # Даем время на скачивание

    driver.close()
    driver.switch_to.window(driver.window_handles[0])


def extract_zip_files(temp_folder: str, mods_folder: str) -> None:
    """Распаковывает все ZIP-файлы из временной папки в папку модов."""
    for filename in os.listdir(temp_folder):
        if filename.endswith(".zip"):
            zip_path = os.path.join(temp_folder, filename)
            try:
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(mods_folder)
                print(f"Распакован: {filename}")
            except Exception as e:
                print(f"Ошибка при распаковке {filename}: {e}")


def read_mod_list(file_path: str) -> List[str]:
    """Читает список модов из файла."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл со списком модов не найден: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def ensure_directory_exists(path: str) -> None:
    """Создает директорию, если она не существует."""
    if not os.path.exists(path):
        os.makedirs(path)


def main() -> None:
    """Основная функция выполнения скрипта."""
    # Настройка путей и временной папки
    script_dir = os.path.dirname(__file__)
    temp_folder = os.path.join(script_dir, "temp")
    
    ensure_directory_exists(temp_folder)
    ensure_directory_exists(MODS_FOLDER)

    # Инициализация драйвера
    driver = setup_driver(temp_folder)
    driver.get("https://www.nexusmods.com")
    time.sleep(3)
    load_cookies(driver)

    try:
        # Чтение и обработка списка модов
        print("Чтение списка модов...")
        mod_names = read_mod_list(MOD_LIST_FILE)
        
        for mod in mod_names:
            try:
                process_single_mod(driver, mod)
            except Exception as e:
                print(f"Ошибка при обработке '{mod}': {e}")

        # Распаковка архивов
        print("Распаковка архивов...")
        extract_zip_files(temp_folder, MODS_FOLDER)

    finally:
        # Завершение работы
        print("Очистка временной папки...")
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder, ignore_errors=True)
        
        driver.quit()
        print("Готово.")


if __name__ == "__main__":
    main()