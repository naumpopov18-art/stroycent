import logging

log_file = None

def debug_log(msg):
    # Используем стандартное логирование вместо print
    logging.debug(msg)
    
    # Сохраняем вашу функциональность с файлом
    if log_file:
        log_file.write(f"[DEBUG] {msg}\n")
        log_file.flush()

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)

# Использование
debug_log("Загрузка этажа 0")
