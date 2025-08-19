from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                               QComboBox, QGridLayout, QDateEdit, QPushButton, QListWidget, 
                               QListWidgetItem, QInputDialog, QColorDialog, QMessageBox, QTextBrowser)
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from stroycent.data_manager import data_store, save_data
from stroycent.utils import debug_log
import re

class StatusEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать статусы кабинетов")
        self.setFixedSize(480, 360)
        
        main_layout = QVBoxLayout()
        
        self.status_list_widget = QListWidget()
        self.update_list()
            
        main_layout.addWidget(self.status_list_widget)
        
        buttons_layout = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        edit_btn = QPushButton("Изменить")
        remove_btn = QPushButton("Удалить")
        
        add_btn.clicked.connect(self.add_status)
        edit_btn.clicked.connect(self.edit_status)
        remove_btn.clicked.connect(self.remove_status)
        
        buttons_layout.addWidget(add_btn)
        buttons_layout.addWidget(edit_btn)
        buttons_layout.addWidget(remove_btn)
        
        main_layout.addLayout(buttons_layout)
        
        self.setLayout(main_layout)
        

    def update_list(self):
        self.status_list_widget.clear()
        for status, colors in data_store['statuses'].items():
            item = QListWidgetItem(f"{status}")
            item.setData(Qt.UserRole, colors)
            item.setBackground(QColor(colors['bg']))
            item.setForeground(QColor(colors['text']))
            self.status_list_widget.addItem(item)
    
    def add_status(self):
        name, ok = QInputDialog.getText(self, "Новый статус", "Введите название статуса:")
        if ok and name:
            bg_color = QColorDialog.getColor(QColor(0, 0, 0, 128), self, "Выберите цвет фона")
            if bg_color.isValid():
                text_color = QColorDialog.getColor(QColor(0, 0, 0, 255), self, "Выберите цвет текста")
                if text_color.isValid():
                    new_status = {
                        name: {
                            "bg": bg_color.name(QColor.HexArgb),
                            "text": text_color.name()
                        }
                    }
                    data_store['statuses'].update(new_status)
                    self.parent().reload_statuses()
                    save_data(data_store)
                    self.update_list()
                
    def edit_status(self):
        current_item = self.status_list_widget.currentItem()
        if not current_item:
            return
            
        old_name = current_item.text()
        old_colors = current_item.data(Qt.UserRole)

        new_name, ok = QInputDialog.getText(self, "Изменить статус", "Новое название:", text=old_name)
        
        if ok and new_name:
            new_bg_color = QColorDialog.getColor(QColor(old_colors['bg']), self, "Выберите новый цвет фона")
            new_text_color = QColorDialog.getColor(QColor(old_colors['text']), self, "Выберите новый цвет текста")

            if new_bg_color.isValid() and new_text_color.isValid():
                data_store['statuses'].pop(old_name)
                data_store['statuses'][new_name] = {
                    "bg": new_bg_color.name(QColor.HexArgb),
                    "text": new_text_color.name()
                }
                self.parent().reload_statuses()
                save_data(data_store)
                self.update_list()

    def remove_status(self):
        current_item = self.status_list_widget.currentItem()
        if not current_item:
            return
            
        name = current_item.text()
        if name in data_store['statuses']:
            del data_store['statuses'][name]
            self.parent().reload_statuses()
            save_data(data_store)
            self.update_list()

class RoomDialog(QDialog):
    def __init__(self, room_data, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.room_data = room_data

        floor_names_map = {
            "0": "Цокольный этаж", "1": "1 этаж", "2": "2 этаж",
            "3": "3 этаж", "4": "4 этаж", "5": "5 этаж"
        }
        
        room_number = self.room_data.get('number', '')
        if not room_number or room_number == "Новый":
            self.setWindowTitle("Введите данные о кабинете")
        else:
            floor_name = floor_names_map.get(str(self.room_data.get('floor')), 'Неизвестный этаж')
            self.setWindowTitle(f"Информация о кабинете № {room_number} на {floor_name}")

        layout = QGridLayout()
        self.inputs = {}
        
        fields = [
            ("Этаж", QLineEdit, True),
            ("Номер кабинета", QLineEdit, False),
            ("ИНН арендатора", QLineEdit, False),
            ("Имя арендатора", QLineEdit, False),
            ("Юридическое наименование арендатора", QLineEdit, False),
            ("Тип оплаты", QComboBox, False),
            ("Дата заезда", QDateEdit, False),
            ("Дата выезда", QDateEdit, False),
            ("Статус", QComboBox, False)
        ]
        
        row = 0
        for label_text, widget_type, read_only in fields:
            lbl = QLabel(label_text)
            widget = None
            if widget_type == QLineEdit:
                widget = QLineEdit()
                widget.setReadOnly(read_only)
                if label_text == "Этаж":
                    floor_name_display = floor_names_map.get(str(self.room_data.get('floor')), 'Неизвестный этаж')
                    widget.setText(floor_name_display)
                if label_text == "ИНН арендатора":
                    widget = QLineEdit()
                    widget.setMaxLength(12)
                    reg_ex = QRegularExpression(r"\d{0,12}")
                    validator = QRegularExpressionValidator(reg_ex)
                    widget.setValidator(validator)
                    widget.setText(str(self.room_data.get("inn", "")))
                    layout.addWidget(lbl, row, 0)
                    layout.addWidget(widget, row, 1)
                    self.inputs[label_text] = widget
                    row += 1
                    continue
                else:
                    key = self.get_data_key(label_text)
                    widget.setText(str(self.room_data.get(key, "")))
                if widget_type == QLineEdit:
                    widget = QLineEdit()
                    widget.setReadOnly(read_only)
                    if label_text == "Этаж":
                        floor_name_display = floor_names_map.get(str(self.room_data.get('floor')), 'Неизвестный этаж')
                        widget.setText(floor_name_display)
                    else:
                        key = self.get_data_key(label_text)
                        widget.setText(str(self.room_data.get(key, "")))

            
            
            elif widget_type == QDateEdit:
                widget = QDateEdit()
                widget.setCalendarPopup(True)
                key = self.get_data_key(label_text)
                date_str = self.room_data.get(key, QDate.currentDate().toString("yyyy-MM-dd"))
                date = QDate.fromString(date_str, "yyyy-MM-dd")
                if not date.isValid() or date > QDate.currentDate():
                    date = QDate.currentDate()
                widget.setDate(date)
                widget.setDisplayFormat("dd.MM.yyyy")

            
            elif widget_type == QComboBox:
                widget = QComboBox()
                if label_text == "Тип оплаты":
                    widget.addItems(["Наличные", "Безналичные"])
                    widget.setCurrentText(self.room_data.get("payment_type", "Наличные"))
                elif label_text == "Статус":
                    widget.addItems(data_store["statuses"].keys())
                    widget.setCurrentText(self.room_data.get("status", "свободный"))

            layout.addWidget(lbl, row, 0)
            layout.addWidget(widget, row, 1)
            self.inputs[label_text] = widget
            row += 1
        
        # Кнопки сохранения, очистки и удаления
        save_btn = QPushButton("Сохранить")
        clear_btn = QPushButton("Очистить данные")
        delete_btn = QPushButton("Удалить кабинет")

        save_btn.clicked.connect(self.save_and_accept)
        clear_btn.clicked.connect(self.confirm_clear_data)
        delete_btn.clicked.connect(self.delete_room)
        
        layout.addWidget(save_btn, row, 0, 1, 2)
        layout.addWidget(clear_btn, row + 1, 0, 1, 2)
        layout.addWidget(delete_btn, row + 2, 0, 1, 2)
        
        self.setLayout(layout)
        self.setFixedWidth(420)

    def get_data_key(self, label_text):
        translations = {
            "ИНН арендатора": "inn",
            "Имя арендатора": "client_name",
            "Юридическое наименование арендатора": "renter_name",
            "Тип оплаты": "payment_type",
            "Дата заезда": "entry_date",
            "Дата выезда": "exit_date",
            "Статус": "status",
            "Номер кабинета": "number",
        }
        return translations.get(label_text)

    def get_data(self, clear=False):
        data = {}
        for label_text, widget in self.inputs.items():
            key = self.get_data_key(label_text)
            if key is None:
                continue
            if isinstance(widget, QLineEdit):
                data[key] = widget.text() if not clear else ""
            elif isinstance(widget, QComboBox):
                data[key] = widget.currentText() if not clear else "Наличные" if key == "payment_type" else "свободный"
            elif isinstance(widget, QDateEdit):
                data[key] = widget.date().toString("yyyy-MM-dd") if not clear else QDate.currentDate().toString("yyyy-MM-dd")
        return data
    

    def validate_data(self, data):
        # Номер кабинета обязателен и не пустой
        if not data.get("number") or data["number"].strip() == "":
            QMessageBox.warning(self, "Ошибка", "Номер кабинета не может быть пустым.")
            return False


        # Даты: дата выезда не может быть раньше даты заезда
        entry_date = QDate.fromString(data.get("entry_date", ""), "yyyy-MM-dd")
        exit_date = QDate.fromString(data.get("exit_date", ""), "yyyy-MM-dd")
        if exit_date < entry_date:
            QMessageBox.warning(self, "Ошибка", "Дата выезда не может быть раньше даты заезда.")
            return False

        return True

    def save_and_accept(self):
        new_data = self.get_data()
        if not self.validate_data(new_data):
            return
        self.room_data.update(new_data)
        save_data(data_store)
        self.accept()
        self.parent_window.update_legend()
        self.parent_window.status.showMessage(f"Данные кабинета {self.room_data.get('number')} сохранены.")

    def confirm_clear_data(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle('Подтверждение')
        msg_box.setText('Вы уверены, что хотите очистить данные?')
        yes_btn = msg_box.addButton("Да", QMessageBox.YesRole)
        no_btn = msg_box.addButton("Нет", QMessageBox.NoRole)
        msg_box.setDefaultButton(no_btn)
        msg_box.exec()
        if msg_box.clickedButton() == yes_btn:
            self.clear_data_only()
            QMessageBox.information(self, 'Успех', 'Данные успешно очищены.')
            self.parent_window.status.showMessage(f"Данные кабинета {self.room_data.get('number')} очищены.")
            self.reject()

    def clear_data_only(self):
        debug_log(f"Очистка данных кабинета {self.room_data.get('number')}")
        self.room_data.update({
            "inn": "",
            "client_name": "",
            "renter_name": "",
            "payment_type": "Наличные",
            "entry_date": QDate.currentDate().toString("yyyy-MM-dd"),
            "exit_date": QDate.currentDate().toString("yyyy-MM-dd"),
            "status": "свободный"
        })
        for label_text, widget in self.inputs.items():
            key = self.get_data_key(label_text)
            if key in self.room_data:
                if isinstance(widget, QLineEdit):
                    widget.setText(self.room_data.get(key, ""))
                elif isinstance(widget, QComboBox):
                    widget.setCurrentText(self.room_data.get(key, ""))
                elif isinstance(widget, QDateEdit):
                    widget.setDate(QDate.fromString(self.room_data.get(key, ""), "yyyy-MM-dd"))
        self.parent_window.update_room_items(self.room_data)
        save_data(data_store)
        self.parent_window.update_legend()

    def delete_room(self):
        debug_log(f"Начало процесса удаления кабинета {self.room_data.get('number')}")
        self.parent_window.delete_room_from_scene_and_data(self.room_data)
        self.reject()

class InstructionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Как пользоваться приложением")
        self.setFixedSize(600, 500)
        
        layout = QVBoxLayout()
        text_browser = QTextBrowser()
        
        instructions = """
        <h1 style='color: #444;'>Инструкция по использованию</h1>
        <p>Добро пожаловать в приложение для управления планом здания. Вот как им пользоваться:</p>
        
        <h2>Кнопки этажей:</h2>
        <ul>
            <li><b>Цокольный этаж, 1 этаж, ...:</b> Используйте эти кнопки для переключения между этажами здания.</li>
        </ul>
        
        <h2>Управление планом:</h2>
        <ul>
            <li><b>Увеличить / Уменьшить:</b> Изменение масштаба плана.</li>
            <li><b>Подогнать под экран:</b> Автоматически масштабирует план, чтобы он полностью поместился в окно.</li>
            <li><b>Загрузить план:</b> Позволяет загрузить изображение (PNG, JPG, BMP) как план текущего этажа.</li>
        </ul>
        
        <h2>Управление кабинетами:</h2>
        <ul>
            <li><b>Добавить кабинет:</b> Активирует режим рисования. Кликните левой кнопкой мыши по плану, чтобы добавить точки полигона. Правый клик завершает рисование и сохраняет новый кабинет.</li>
            <li><b>Изменить статусы кабинетов:</b> Открывает диалог для добавления, изменения или удаления статусов (например, "свободный", "занят") и их цветов.</li>
        </ul>
        
        <h2>Работа с полигоном кабинета:</h2>
        <ul>
            <li><b>Клик по кабинету:</b> Открывает модальное окно для ввода и редактирования информации о кабинете (номер, арендатор, даты, статус).</li>
            <li><b>В модальном окне:</b>
                <ul>
                    <li><b>Сохранить:</b> Сохраняет введенные данные.</li>
                    <li><b>Очистить данные:</b> Удаляет всю текстовую информацию о кабинете (арендатор, даты), но оставляет его форму на карте.</li>
                    <li><b>Удалить кабинет:</b> Полностью удаляет полигон кабинета с карты и его данные из системы.</li>
                </ul>
            </li>
        </ul>
        """
        text_browser.setHtml(instructions)
        layout.addWidget(text_browser)
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)

class ReportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Сводный отчет по кабинетам")
        self.setFixedSize(600, 400)
        
        layout = QVBoxLayout()
        self.report_text = QTextBrowser()
        layout.addWidget(self.report_text)
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
        self.update_report()
        
    def update_report(self):
        html_content = ""
        total_rooms = 0
        status_counts = {}
        
        for floor_data in data_store["floors"].values():
            for room_data in floor_data.get("rooms", []):
                total_rooms += 1
                status = room_data.get("status", "свободный")
                status_counts[status] = status_counts.get(status, 0) + 1
        
        html_content += f"<h2>Сводка по всем кабинетам</h2>"
        html_content += f"<p>Всего кабинетов: <b>{total_rooms}</b></p>"
        
        if total_rooms > 0:
            html_content += f"<h3>Загрузка:</h3><ul>"
            for status, count in status_counts.items():
                percentage = (count / total_rooms) * 100
                html_content += f"<li><b>{status}</b>: {count} ({percentage:.1f}%)</li>"
            html_content += "</ul>"
        
        html_content += "<h3>Разбивка по этажам:</h3>"
        
        floor_names_map = {
            "0": "Цокольный этаж", "1": "1 этаж", "2": "2 этаж",
            "3": "3 этаж", "4": "4 этаж", "5": "5 этаж"
        }
        
        sorted_floors = sorted(data_store["floors"].keys(), key=int)
        
        for floor_key in sorted_floors:
            floor_data = data_store["floors"][floor_key]
            rooms_on_floor = floor_data.get("rooms", [])
            floor_name = floor_names_map.get(floor_key, f"{floor_key} этаж")
            
            floor_status_counts = {status: 0 for status in data_store['statuses'].keys()}
            
            for room in rooms_on_floor:
                status = room.get("status", "свободный")
                floor_status_counts[status] = floor_status_counts.get(status, 0) + 1
            
            html_content += f"<p><b>{floor_name}</b> (Всего кабинетов: {len(rooms_on_floor)})</p><ul>"
            
            for status, count in floor_status_counts.items():
                if count > 0:
                    html_content += f"<li>{status}: {count}</li>"
            
            html_content += "</ul>"
            
        self.report_text.setHtml(html_content)
