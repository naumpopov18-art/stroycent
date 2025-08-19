import sys
import os
import json
import shutil

DEFAULT_STATUSES = {
    "свободный": {"bg": "#B300ff00", "text": "#000000"},
    "занят": {"bg": "#B3ffff00", "text": "#000000"},
    "скоро освободится": {"bg": "#B3ffa500", "text": "#000000"},
    "в ремонте": {"bg": "#B3ff0000", "text": "#ffffff"}
}

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_data_file_path():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, "building_data.json")

def get_log_file_path():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, "error_log.txt")

def ensure_data_file_exists():
    target_path = get_data_file_path()
    if not os.path.exists(target_path):
        try:
            source_path = get_resource_path("building_data.json")
            shutil.copyfile(source_path, target_path)
        except Exception as e:
            print(f"Ошибка копирования building_data.json: {e}")

def load_data():
    if os.path.exists(get_data_file_path()):
        try:
            with open(get_data_file_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
                if 'statuses' not in data:
                    data['statuses'] = DEFAULT_STATUSES
                return data
        except Exception:
            return {"floors": {}, "statuses": DEFAULT_STATUSES}
    else:
        return {"floors": {}, "statuses": DEFAULT_STATUSES}

def save_data(data):
    try:
        with open(get_data_file_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка при сохранении данных: {e}")

# Инициализация данных при импорте
ensure_data_file_exists()
data_store = load_data()
