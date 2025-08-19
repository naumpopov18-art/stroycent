import traceback
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,QGraphicsTextItem,QGraphicsPolygonItem, QGraphicsScene, QSizePolicy, QStatusBar, QLabel, QFileDialog
from PySide6.QtGui import QPixmap, QPainter, QColor, QBrush, QFont
from PySide6.QtCore import Qt, QPointF, QTimer
from functools import partial
from stroycent.graphics import DrawingGraphicsView, QPolygonF
from stroycent.dialogs import RoomDialog, StatusEditorDialog, InstructionsDialog, ReportDialog
from stroycent.data_manager import data_store, save_data
from stroycent.utils import debug_log
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("План здания")
        
        # Установка начального размера окна
        self.resize(1200, 800)
        
        container = QWidget()
        main_layout = QVBoxLayout()
        
        self.floor_buttons_layout = QHBoxLayout()
        floor_names = ["Цокольный этаж", "1 этаж", "2 этаж", "3 этаж", "4 этаж", "5 этаж"]
        self.floor_buttons = []
        for i, name in enumerate(floor_names):
            btn = QPushButton(name)
            btn.setProperty("floor_index", i)
            btn.clicked.connect(lambda checked, f=i: self.load_floor(f))
            self.floor_buttons_layout.addWidget(btn)
            self.floor_buttons.append(btn)
        main_layout.addLayout(self.floor_buttons_layout)
        
        self.scene = QGraphicsScene()
        self.view = DrawingGraphicsView(self.scene, self, parent=container)
        self.view.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.view)
        
        controls_layout = QHBoxLayout()
        
        zoom_in_btn = QPushButton("Увеличить")
        zoom_in_btn.setToolTip("Увеличить")
        zoom_in_btn.clicked.connect(lambda: self.view.scale(1.2, 1.2))
        zoom_out_btn = QPushButton("Уменьшить")
        zoom_out_btn.setToolTip("Уменьшить")
        zoom_out_btn.clicked.connect(lambda: self.view.scale(0.8, 0.8))
        controls_layout.addWidget(zoom_in_btn)
        controls_layout.addWidget(zoom_out_btn)

        fit_to_view_btn = QPushButton("Подогнать под экран")
        fit_to_view_btn.setToolTip("Подогнать план под размер окна")
        fit_to_view_btn.clicked.connect(self.fit_plan_to_view)
        controls_layout.addWidget(fit_to_view_btn)

        self.add_room_btn = QPushButton("Добавить кабинет")
        self.add_room_btn.setToolTip("Начать рисование нового полигона")
        self.add_room_btn.clicked.connect(self.start_drawing)

        controls_layout.addWidget(self.add_room_btn)
        
        self.upload_plan_btn = QPushButton("Загрузить план")
        self.upload_plan_btn.setToolTip("Загрузить новый план этажа")
        self.upload_plan_btn.clicked.connect(self.upload_plan)
        controls_layout.addWidget(self.upload_plan_btn)

        self.edit_statuses_btn = QPushButton("Изменить статусы кабинетов")
        self.edit_statuses_btn.setToolTip("Добавить/удалить/изменить статусы и их цвета")
        self.edit_statuses_btn.clicked.connect(self.open_status_editor)
        controls_layout.addWidget(self.edit_statuses_btn)
        
        # Новая кнопка "Как пользоваться приложением"
        self.instructions_btn = QPushButton("Как пользоваться приложением")
        self.instructions_btn.clicked.connect(self.open_instructions_dialog)
        controls_layout.addWidget(self.instructions_btn)

        # Новая кнопка "Отчет"
        self.report_btn = QPushButton("Отчет")
        self.report_btn.setToolTip("Показать сводку по всем кабинетам")
        self.report_btn.clicked.connect(self.open_report_dialog)
        controls_layout.addWidget(self.report_btn)

        main_layout.addLayout(controls_layout)
        
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.setStyleSheet("color: #f7f7f7;")
        
        # --- НОВАЯ ФУНКЦИОНАЛЬНОСТЬ: ЛЕГЕНДА СТАТУСОВ ---
        self.legend_widget = QWidget()
        self.legend_layout = QHBoxLayout(self.legend_widget)
        self.legend_layout.setContentsMargins(10, 0, 10, 0)
        self.legend_layout.setSpacing(15)
        # Добавляем легенду в правый край статус-бара
        self.status.addPermanentWidget(self.legend_widget)
        
        # Обновляем легенду сразу при запуске
        self.update_legend()
        # --- КОНЕЦ НОВОЙ ФУНКЦИОНАЛЬНОСТИ ---
        
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        
        self.view.drawing_finished.connect(self.finish_drawing)
        
        self.current_floor = 0
        self.editing_room_data = None
        self.is_adding_mode = False
        self.is_editing_mode = False
        self.floor_item = None
        self.room_items = {} # Словарь для хранения ссылок на графические объекты
        
        # Загружаем первый этаж сразу, чтобы план был виден при запуске
        self.load_floor(0) 

    def open_instructions_dialog(self):
        """Открывает модальное окно с инструкцией."""
        dlg = InstructionsDialog(self)
        dlg.exec()

    def open_report_dialog(self):
        """Открывает модальное окно с отчетом."""
        dlg = ReportDialog(self)
        dlg.exec()

    def reset_drawing_state(self):
        """Сбрасывает состояние рисования в главном окне."""
        self.is_adding_mode = False
        self.is_editing_mode = False
        self.add_room_btn.setText("Добавить кабинет")
        self.status.showMessage("")
        self.editing_room_data = None
        self.view.stop_drawing_mode()

    def resizeEvent(self, event):
        """
        Обрабатывает изменение размера окна и вызывает подгонку под экран.
        """
        super().resizeEvent(event)
        QTimer.singleShot(0, self.fit_plan_to_view)

    def fit_plan_to_view(self):
        """Автоматически масштабирует план так, чтобы он вписывался в виджет."""
        # Убеждаемся, что у нас есть элемент для масштабирования
        if self.floor_item and self.view.rect().size().isValid():
            self.view.fitInView(self.floor_item, Qt.KeepAspectRatio)

    def start_drawing(self):
        if self.is_adding_mode or self.is_editing_mode or self.view.is_drawing:
            self.status.showMessage("Завершите текущее действие перед добавлением нового кабинета.")
            return
        self.is_adding_mode = True
        self.is_editing_mode = False
        self.view.start_drawing_mode()
        self.add_room_btn.setText("Рисуем... (правый клик - готово)")
        self.status.showMessage("Кликните левой кнопкой мыши, чтобы добавить точки полигона. Правый клик завершает рисование.")
        self.editing_room_data = None
    
    def get_next_room_number(self):
        """Находит следующий доступный номер для кабинета."""
        floor_rooms = data_store["floors"].get(str(self.current_floor), {}).get("rooms", [])
        existing_numbers = [
            int(room['number']) for room in floor_rooms
            if room.get('number', '').isdigit()
        ]
        return max(existing_numbers) + 1 if existing_numbers else 1

    def finish_drawing(self, points):
        """
        Обрабатывает завершение рисования, создавая или обновляя полигон.
        """
        try:
            if self.is_editing_mode and self.editing_room_data:
                room_data_to_save = self.editing_room_data
                room_data_to_save["points"] = [[p.x(), p.y()] for p in points]
            else:
                room_number = str(self.get_next_room_number())
                room_data_to_save = {
                    "number": room_number,
                    "floor": str(self.current_floor),
                    "status": "свободный",
                    "points": [[p.x(), p.y()] for p in points],
                    "renter_name": ""
                }
                floor_data = data_store["floors"].setdefault(str(self.current_floor), {"rooms": []})
                floor_data["rooms"].append(room_data_to_save)

            save_data(data_store)
            
            self.reset_drawing_state()
            self.status.showMessage("Готово. Вы можете продолжить рисование.")
            self.load_floor(self.current_floor) # Полная перезагрузка для чистоты

        except Exception as e:
            self.status.showMessage(f"Ошибка при завершении рисования: {e}")
            debug_log(f"Ошибка при завершении рисования: {traceback.format_exc()}")
        
    def load_floor(self, floor):
        """
        Загружает изображение этажа и рисует на нем полигоны.
        """
        try:
            debug_log(f"Загрузка этажа {floor}")
            
            # Сбрасываем состояние рисования перед загрузкой нового этажа
            self.reset_drawing_state()
            
            self.scene.clear()
            self.room_items.clear()
            self.current_floor = floor
            
            floor_data = data_store["floors"].setdefault(str(floor), {"rooms": []})
            img_path = floor_data.get("plan_path")
            
            pixmap = None
            if img_path and os.path.exists(img_path):
                debug_log(f"Файл найден: {img_path}")
                pixmap = QPixmap(img_path)
            
            if not pixmap or pixmap.isNull():
                debug_log("Файл не найден или ошибка загрузки, создаем заглушку")
                pixmap = QPixmap(1000, 800)
                pixmap.fill(Qt.lightGray)
            
            self.floor_item = self.scene.addPixmap(pixmap)
            
            QTimer.singleShot(0, self.fit_plan_to_view)

            self.set_active_floor_button(floor)
            floor_names = ["Цокольный этаж", "1 этаж", "2 этаж", "3 этаж", "4 этаж", "5 этаж"]
            self.status.showMessage(f"Выбран: {floor_names[floor]}")

            for room_data in floor_data["rooms"]:
                if 'points' in room_data:
                    self.draw_room_polygon(room_data)
                else:
                    debug_log(f"Пропущено некорректное помещение без данных о полигоне: {room_data}")
                
        except Exception as e:
            self.status.showMessage(f"Ошибка при загрузке этажа: {e}")
            debug_log(f"Ошибка при загрузке этажа: {traceback.format_exc()}")

    def set_active_floor_button(self, floor_index):
        """Устанавливает стиль для активной кнопки этажа."""
        for i, btn in enumerate(self.floor_buttons):
            if i == floor_index:
                btn.setStyleSheet("background-color: #5c5c5c; color: #f7f7f7; font-weight: bold;")
            else:
                btn.setStyleSheet("background-color: #f7f7f7; color: #3c3c3c;")

    def upload_plan(self):
        """Открывает диалог для выбора нового плана этажа."""
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Выберите новый план этажа")
        file_path, _ = file_dialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.bmp)")
        if file_path:
            debug_log(f"Выбран файл: {file_path}")
            floor_data = data_store["floors"].setdefault(str(self.current_floor), {"rooms": []})
            floor_data["plan_path"] = file_path
            save_data(data_store)
            self.load_floor(self.current_floor)

    def draw_room_polygon(self, room_data):
        """
        Создает и рисует полигон для кабинета на сцене.
        Сохраняет ссылки на графические элементы в словаре self.room_items.
        """
        try:
            debug_log(f"Создаем полигон для кабинета {room_data.get('number')}")
            
            points = [QPointF(x, y) for x, y in room_data.get("points", [])]
            polygon = QPolygonF(points)
            
            # Создаем полигон
            item = QGraphicsPolygonItem(polygon)
            item.setData(0, room_data)
            
            status = room_data.get("status", "свободный")
            colors = data_store["statuses"].get(status, {"bg": "#B3808080", "text": "#000000"})
            
            item.setBrush(QBrush(QColor(colors["bg"])))
            
            item.setFlag(QGraphicsPolygonItem.ItemIsSelectable, True)
            item.mousePressEvent = partial(self.polygon_clicked, room_data=room_data)
            self.scene.addItem(item)
            
            bounding_rect = polygon.boundingRect()

            # Создаем элемент для номера кабинета
            number_text = f"Каб. № {room_data.get('number', 'N/A')}"
            number_text_item = QGraphicsTextItem(number_text)
            number_text_item.setDefaultTextColor(QColor(colors["text"]))
            number_font = QFont("Arial", 30, QFont.Bold)
            number_text_item.setFont(number_font)
            
            # Устанавливаем позицию текста с отступом 30px от верхнего и левого края
            number_x = bounding_rect.x() + 30
            number_y = bounding_rect.y() + 30
            number_text_item.setPos(number_x, number_y)
            self.scene.addItem(number_text_item)
            
            # Создаем элемент для названия компании
            renter_name = room_data.get('renter_name', 'Нет арендатора')
            if len(renter_name) > 20:
                renter_name = renter_name[:17] + "..."
            
            renter_text_item = QGraphicsTextItem(renter_name)
            renter_text_item.setDefaultTextColor(QColor(colors["text"]))
            renter_font = QFont("Arial", 24, QFont.Bold)
            renter_text_item.setFont(renter_font)
            
            # Устанавливаем позицию текста под номером кабинета с небольшим отступом
            renter_y = number_y + number_text_item.boundingRect().height() + 10
            renter_text_item.setPos(number_x, renter_y)
            self.scene.addItem(renter_text_item)

            # Сохраняем ссылки на элементы
            self.room_items[room_data.get('number')] = {
                'polygon': item,
                'number_text': number_text_item,
                'renter_text': renter_text_item
            }
            
            return item, number_text_item, renter_text_item
        except Exception as e:
            self.status.showMessage(f"Ошибка при отрисовке полигона: {e}")
            debug_log(f"Ошибка при отрисовке полигона: {traceback.format_exc()}")


    def polygon_clicked(self, event, room_data):
        if event.button() == Qt.LeftButton:
            dlg = RoomDialog(room_data, self)
            if dlg.exec():
                save_data(data_store)
                self.update_room_items(room_data)
                self.status.showMessage(f"Сохранено: кабинет {room_data.get('number', 'Новый')}")
        elif event.button() == Qt.RightButton:
            if not self.view.is_drawing and not self.is_adding_mode:
                self.editing_room_data = room_data
                initial_points = [QPointF(x, y) for x, y in room_data.get("points", [])]
                items = self.room_items.get(room_data.get('number'))
                if items:
                    items['polygon'].setVisible(False)
                    items['number_text'].setVisible(False)
                    items['renter_text'].setVisible(False)
                self.view.start_drawing_mode(initial_points=initial_points)
                self.add_room_btn.setText("Редактирование... (правый клик - готово)")
                self.status.showMessage("Меняйте форму полигона. Backspace для удаления точки. Правый клик завершает редактирование.")
                self.is_editing_mode = True
                self.is_adding_mode = False

    def update_room_items(self, room_data):
        """
        Обновляет внешний вид полигона и текста на сцене,
        используя прямой доступ через словарь self.room_items.
        """
        try:
            debug_log(f"Обновление элементов для кабинета {room_data.get('number')}")
            
            room_number = room_data.get('number')
            if room_number in self.room_items:
                items = self.room_items[room_number]
                item = items['polygon']
                number_text_item = items['number_text']
                renter_text_item = items['renter_text']

                status = room_data.get("status", "свободный")
                colors = data_store["statuses"].get(status, {"bg": "#B3808080", "text": "#000000"})
                item.setBrush(QBrush(QColor(colors["bg"])))
                debug_log(f"Обновлен цвет полигона на {colors['bg']}")
                
                # Обновляем текст
                number_text = f"Каб. № {room_data.get('number', 'N/A')}"
                renter_name = room_data.get('renter_name', 'Нет арендатора')
                if len(renter_name) > 20:
                    renter_name = renter_name[:17] + "..."
                
                number_text_item.setPlainText(number_text)
                renter_text_item.setPlainText(renter_name)
                
                # Обновляем цвета текста
                number_text_item.setDefaultTextColor(QColor(colors["text"]))
                renter_text_item.setDefaultTextColor(QColor(colors["text"]))
                
                # Пересчитываем позицию текста
                bounding_rect = item.polygon().boundingRect()
                number_x = bounding_rect.x() + 30
                number_y = bounding_rect.y() + 30
                renter_y = number_y + number_text_item.boundingRect().height() + 10
                
                number_text_item.setPos(number_x, number_y)
                renter_text_item.setPos(number_x, renter_y)
                
                debug_log(f"Обновлен текст и его цвет на {colors['text']}")
            else:
                debug_log(f"Не удалось найти элементы для кабинета {room_number} в словаре.")
            # Добавляем вызов обновления легенды
            self.update_legend()
        except Exception as e:
            self.status.showMessage(f"Ошибка при обновлении элементов: {e}")
            debug_log(f"Ошибка при обновлении элементов: {traceback.format_exc()}")
            
    def delete_room_from_scene_and_data(self, room_data_to_delete):
        """
        Удаляет полигон и его данные.
        """
        try:
            debug_log(f"Удаление кабинета: {room_data_to_delete.get('number')}")
            floor_rooms = data_store["floors"].get(str(self.current_floor), {}).get("rooms", [])

            if room_data_to_delete in floor_rooms:
                floor_rooms.remove(room_data_to_delete)
                save_data(data_store)
                self.status.showMessage(f"Кабинет {room_data_to_delete.get('number')} удален.")
                
                # Находим и удаляем элементы на сцене и в словаре
                room_number = room_data_to_delete.get('number')
                if room_number in self.room_items:
                    items = self.room_items.pop(room_number)
                    self.scene.removeItem(items['polygon'])
                    self.scene.removeItem(items['number_text'])
                    self.scene.removeItem(items['renter_text'])
                
                # Сбрасываем состояние рисования после удаления
                self.reset_drawing_state()
                self.load_floor(self.current_floor)
            else:
                self.status.showMessage("Не удалось найти данные для удаления.")
        except Exception as e:
            self.status.showMessage(f"Ошибка при удалении кабинета: {e}")
            debug_log(f"Ошибка при удалении кабинета: {traceback.format_exc()}")

    def open_status_editor(self):
        """Открывает окно для редактирования статусов."""
        dlg = StatusEditorDialog(self)
        dlg.exec()
        self.reload_statuses()
        self.update_legend()

    def reload_statuses(self):
        """
        Обновляет статусы во всех кабинетах после их редактирования.
        Также вызывает обновление легенды.
        """
        for room_data in data_store["floors"].get(str(self.current_floor), {}).get("rooms", []):
            self.update_room_items(room_data)
        self.status.showMessage("Статусы кабинетов обновлены.")
        self.update_legend() # Вызываем обновление легенды

    def update_legend(self):
        """
        Создает и обновляет легенду статусов в статус-баре,
        включая количество кабинетов по каждому статусу.
        """
        # Очищаем старую легенду
        while self.legend_layout.count():
            child = self.legend_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # --- НОВАЯ ЛОГИКА ПОДСЧЕТА ---
        status_counts = {}
        # Инициализируем словарь подсчета для всех известных статусов
        for status in data_store["statuses"].keys():
            status_counts[status] = 0
            
        # Проходим по всем этажам и кабинетам, чтобы посчитать их статусы
        for floor_data in data_store["floors"].values():
            for room_data in floor_data.get("rooms", []):
                status = room_data.get("status", "свободный")
                if status in status_counts:
                    status_counts[status] += 1
                else:
                    # Если статус есть в данных, но не в словаре статусов,
                    # можно добавить его сюда с предупреждением
                    status_counts[status] = 1
        # --- КОНЕЦ НОВОЙ ЛОГИКИ ---
        
        # Добавляем новые элементы, используя данные о количестве
        for status, colors in data_store["statuses"].items():
            # Квадратик цвета
            color_label = QLabel()
            color_label.setFixedSize(16, 16)
            color_label.setStyleSheet(f"background-color: {colors['bg']}; border: 1px solid white; border-radius: 4px;")
            
            # Текст статуса и количество
            count = status_counts.get(status, 0)
            status_label = QLabel(f"{status} ({count})")
            status_label.setStyleSheet("color: #f7f7f7;")
            
            self.legend_layout.addWidget(color_label)
            self.legend_layout.addWidget(status_label)

