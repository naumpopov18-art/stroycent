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
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    # Для .app структуры ищем в Resources
    resources_path = os.path.join(base_path, '..', 'Resources')
    if os.path.exists(os.path.join(resources_path, relative_path)):
        return os.path.join(resources_path, relative_path)
    
    return os.path.join(base_path, relative_path)

def get_data_file_path():
    """Путь к файлу данных (всегда рядом с исполняемым файлом)"""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, "building_data.json")

def get_log_file_path():
    """Путь к файлу логов (всегда рядом с исполняемым файлом)"""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, "error_log.txt")

def ensure_data_file_exists():
    """Создает файл данных если его нет, копируя из ресурсов"""
    target_path = get_data_file_path()
    if not os.path.exists(target_path):
        try:
            # Пробуем несколько возможных путей к исходному файлу
            possible_sources = [
                get_resource_path("building_data.json"),  # Для PyInstaller .app
                os.path.join(os.path.dirname(__file__), "building_data.json"),  # Для разработки
                "building_data.json"  # Относительный путь
            ]
            
            for source_path in possible_sources:
                if os.path.exists(source_path):
                    shutil.copyfile(source_path, target_path)
                    print(f"Файл данных скопирован из: {source_path}")
                    return
            
            # Если файл не найден нигде, создаем пустой
            print("Исходный файл данных не найден, создаем новый")
            initial_data = {"floors": {}, "statuses": DEFAULT_STATUSES}
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=4, ensure_ascii=False)
                
        except Exception as e:
            print(f"Ошибка создания building_data.json: {e}")
            # Создаем минимальный файл данных
            initial_data = {"floors": {}, "statuses": DEFAULT_STATUSES}
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=4, ensure_ascii=False)

def load_data():
    """Загрузка данных из файла"""
    data_file = get_data_file_path()
    if os.path.exists(data_file):
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure statuses exist
                if 'statuses' not in data:
                    data['statuses'] = DEFAULT_STATUSES.copy()
                # Ensure all default statuses exist
                for status, colors in DEFAULT_STATUSES.items():
                    if status not in data['statuses']:
                        data['statuses'][status] = colors
                return data
        except Exception as e:
            print(f"Ошибка загрузки данных: {e}")
            return {"floors": {}, "statuses": DEFAULT_STATUSES.copy()}
    else:
        return {"floors": {}, "statuses": DEFAULT_STATUSES.copy()}

def save_data(data):
    """Сохранение данных в файл"""
    try:
        with open(get_data_file_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка при сохранении данных: {e}")

# Инициализация данных при импорте
ensure_data_file_exists()
data_store = load_data()
