from PySide6.QtWidgets import QApplication
import sys
from stroycent.app import MainWindow
from stroycent.data_manager import get_log_file_path
import traceback
import os

def load_stylesheet(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    log_file = None
    try:
        log_file = open(get_log_file_path(), "w", encoding="utf-8")
        log_file.write("--- Начало сеанса ---\n")
        log_file.flush()
        app = QApplication(sys.argv)
        css_path = os.path.join(os.path.dirname(__file__), "styles", "main.css")
        if os.path.exists(css_path):
            stylesheet = load_stylesheet(css_path)
            app.setStyleSheet(stylesheet)
        else:
            print(f"Файл стилей не найден: {css_path}")

        window = MainWindow()
        window.show()

        sys.exit(app.exec())

    except Exception:
        if log_file and not log_file.closed:
            log_file.write("\n" + "="*50 + "\n")
            log_file.write("Произошла критическая ошибка! Приложение будет закрыто.\n")
            traceback.print_exc(file=log_file)
            log_file.write("="*50 + "\n\n")
            log_file.flush()

    finally:
        if log_file and not log_file.closed:
            log_file.write("--- Конец сеанса ---\n")
            log_file.close()

