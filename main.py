from PySide6.QtWidgets import QApplication
import sys
from stroycent.app import MainWindow
from stroycent.data_manager import get_log_file_path
import traceback
import os

def resource_path(relative_path):
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

def load_stylesheet():
    """Загрузка стилей с учетом разных режимов запуска"""
    try:
        # Определяем базовый путь в зависимости от режима
        if getattr(sys, 'frozen', False):
            # Режим собранного приложения
            if hasattr(sys, '_MEIPASS'):
                # .app bundle режим
                base_path = sys._MEIPASS
            else:
                # onefile режим
                base_path = os.path.dirname(sys.executable)
        else:
            # Режим разработки
            base_path = os.path.dirname(__file__)
        
        # Пробуем несколько возможных путей
        possible_paths = [
            os.path.join(base_path, "styles", "main.css"),
            os.path.join(base_path, "..", "Resources", "styles", "main.css"),
            os.path.join(base_path, "Resources", "styles", "main.css"),
            "styles/main.css"
        ]
        
        for css_path in possible_paths:
            if os.path.exists(css_path):
                print(f"[DEBUG] Найден файл стилей: {css_path}")
                with open(css_path, "r", encoding="utf-8") as f:
                    return f.read()
        
        print("[DEBUG] Файл стилей не найден ни по одному из путей:")
        for path in possible_paths:
            print(f"  - {path}")
        return ""
        
    except Exception as e:
        print(f"[DEBUG] Ошибка загрузки стилей: {e}")
        return ""

if __name__ == "__main__":
    log_file = None
    try:
        log_file = open(get_log_file_path(), "w", encoding="utf-8")
        log_file.write("--- Начало сеанса ---\n")
        log_file.flush()
        
        app = QApplication(sys.argv)
        
        # Загрузка стилей
        stylesheet = load_stylesheet()
        if stylesheet:
            app.setStyleSheet(stylesheet)
            if log_file:
                log_file.write("Стили успешно загружены\n")
        else:
            if log_file:
                log_file.write("Стили не загружены - файл не найден\n")

        window = MainWindow()
        window.show()

        sys.exit(app.exec())

    except Exception as e:
        if log_file and not log_file.closed:
            log_file.write("\n" + "="*50 + "\n")
            log_file.write("Произошла критическая ошибка! Приложение будет закрыто.\n")
            log_file.write(f"Ошибка: {str(e)}\n")
            traceback.print_exc(file=log_file)
            log_file.write("="*50 + "\n\n")
            log_file.flush()
        # Повторно выводим в консоль для отладки
        traceback.print_exc()

    finally:
        if log_file and not log_file.closed:
            log_file.write("--- Конец сеанса ---\n")
            log_file.close()
