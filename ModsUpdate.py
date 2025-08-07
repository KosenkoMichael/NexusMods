import os
import json
import time
import shutil
import zipfile
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib.parse
from typing import Dict, List, Optional, Any

from config import MOD_NAME_TO_ID, MOD_LIST_FILE, MODS_FOLDER, GAME_DOMAIN

logger = logging.getLogger("NexusModDownloader")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def setup_driver(temp_folder: str) -> webdriver.Chrome:
    options = Options()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-logging")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    prefs = {
        "download.default_directory": temp_folder,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    options.add_experimental_option("prefs", prefs)

    return webdriver.Chrome(options=options)


def load_cookies(driver: webdriver.Chrome, cookies_file: str = "cookies.json") -> None:
    if not os.path.exists(cookies_file):
        logger.warning(
            f"Файл {cookies_file} не найден. Авторизация не будет выполнена."
        )
        return

    with open(cookies_file, "r", encoding="utf-8") as f:
        cookies = json.load(f)
        for cookie in cookies:
            cookie.pop("sameSite", None)
            cookie.pop("priority", None)
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                logger.warning(f"[Cookie Error] {e}")

    driver.refresh()
    time.sleep(3)


def load_json(filepath: str) -> Dict[str, Any]:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"[Ошибка] Не удалось прочитать JSON-файл '{filepath}': {e}")
        return {}


def save_json(data: Dict[str, Any], filepath: str) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def compare_versions(v1: str, v2: str) -> int:
    parts1 = [int(p) for p in v1.split(".")]
    parts2 = [int(p) for p in v2.split(".")]
    max_length = max(len(parts1), len(parts2))
    parts1.extend([0] * (max_length - len(parts1)))
    parts2.extend([0] * (max_length - len(parts2)))
    for p1, p2 in zip(parts1, parts2):
        if p1 < p2:
            return -1
        elif p1 > p2:
            return 1
    return 0


def get_mod_version(driver: webdriver.Chrome) -> Optional[str]:
    try:
        version_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "li.stat-version div.stat")
            )
        )
        return version_element.text.strip()
    except Exception as e:
        logger.warning(f"Не удалось получить версию мода: {e}")
        return None


def download_mod_file(driver: webdriver.Chrome, mod_id: int) -> bool:
    try:
        logger.info(f"Переход к странице мода ID {mod_id}...")
        driver.get(f"https://www.nexusmods.com/{GAME_DOMAIN}/mods/{mod_id}")

        current_version = get_mod_version(driver)
        if not current_version:
            logger.warning("Не удалось определить версию мода.")
            return False

        versions_data = load_json("versions.json")
        if str(mod_id) in versions_data:
            comparison = compare_versions(current_version, versions_data[str(mod_id)])
            if comparison == 0:
                logger.info(f"Мод {mod_id} уже актуален (версия {current_version})")
                return True
            elif comparison < 0:
                logger.info(
                    f"Локальная версия ({versions_data[str(mod_id)]}) новее, чем на сайте ({current_version})"
                )
                return False

        manual_link = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(translate(., 'MANUAL', 'manual'), 'manual')]")
            )
        )
        manual_url = manual_link.get_attribute("href")
        if manual_url.startswith("/"):
            manual_url = urllib.parse.urljoin("https://www.nexusmods.com", manual_url)

        logger.info("Переход к странице загрузки Manual...")
        driver.get(manual_url)

        slow_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "slowDownloadButton"))
        )
        slow_button.click()
        logger.info("Скачивание через 'Slow Download' запущено...")
        time.sleep(5)

        versions_data[str(mod_id)] = current_version
        save_json(versions_data, "versions.json")
        return True

    except Exception as e:
        logger.error(f"Ошибка при скачивании мода {mod_id}: {e}")
        return False


def process_single_mod(driver: webdriver.Chrome, mod_name: str) -> None:
    mod_id = MOD_NAME_TO_ID.get(mod_name)
    if not mod_id:
        logger.warning(f"Мод '{mod_name}' не найден в словаре ID.")
        return

    logger.info(
        f"\n==============================\nОбработка мода: {mod_name} (ID: {mod_id})\n=============================="
    )

    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[-1])

    if download_mod_file(driver, mod_id):
        time.sleep(5)

    driver.close()
    driver.switch_to.window(driver.window_handles[0])


def extract_zip_files(temp_folder: str, mods_folder: str) -> None:
    for filename in os.listdir(temp_folder):
        if filename.endswith(".zip"):
            zip_path = os.path.join(temp_folder, filename)
            try:
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(mods_folder)
                logger.info(f"Распакован архив: {filename}")
            except Exception as e:
                logger.error(f"Ошибка при распаковке {filename}: {e}")


def read_mod_list(file_path: str) -> List[str]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл со списком модов не найден: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def ensure_directory_exists(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path)


def main() -> None:
    script_dir = os.path.dirname(__file__)
    temp_folder = os.path.join(script_dir, "temp")

    ensure_directory_exists(temp_folder)
    ensure_directory_exists(MODS_FOLDER)

    logger.info("Запуск драйвера Chrome...")
    driver = setup_driver(temp_folder)
    driver.get("https://www.nexusmods.com")
    time.sleep(3)
    load_cookies(driver)

    try:
        logger.info("Чтение списка модов...")
        mod_names = read_mod_list(MOD_LIST_FILE)

        for mod in mod_names:
            try:
                process_single_mod(driver, mod)
            except Exception as e:
                logger.error(f"Ошибка при обработке мода '{mod}': {e}")

        logger.info("Распаковка всех загруженных архивов...")
        extract_zip_files(temp_folder, MODS_FOLDER)

    finally:
        logger.info("Очистка временной папки...")
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder, ignore_errors=True)

        driver.quit()
        logger.info("Готово. Все операции завершены.")


if __name__ == "__main__":
    main()
