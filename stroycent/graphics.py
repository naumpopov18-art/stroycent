from PySide6.QtWidgets import QGraphicsView, QGraphicsPolygonItem, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsItem
from PySide6.QtCore import Qt, QPointF, Signal, QObject
from PySide6.QtGui import QPen, QBrush, QColor, QPolygonF, QPainterPath, QFont
from functools import partial
from stroycent.utils import debug_log

class DraggablePointItem(QObject, QGraphicsEllipseItem):
    point_moved = Signal(int, QPointF)

    def __init__(self, x, y, size, index, parent=None):
        QObject.__init__(self, parent)
        QGraphicsEllipseItem.__init__(self, x - size/2, y - size/2, size, size)
        self.setPen(QPen(Qt.black, 1))
        self.setBrush(QBrush(Qt.red))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setCursor(Qt.PointingHandCursor)
        self.index = index
        self.initial_pos = None

    def mousePressEvent(self, event):
        self.initial_pos = self.scenePos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        new_pos = self.scenePos()
        if new_pos != self.initial_pos:
            self.point_moved.emit(self.index, new_pos)
        super().mouseReleaseEvent(event)

class DrawingGraphicsView(QGraphicsView):
    drawing_finished = Signal(object)

    def __init__(self, scene, main_window, parent=None):
        super().__init__(scene, parent)
        self.main_window = main_window
        self.setMouseTracking(True)
        self.is_drawing = False
        self.drawing_points = []
        self.drawing_path_item = None
        self.point_items = []

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

    def wheelEvent(self, event):
        if self.is_drawing:
            return
        zoom_factor = 1.1
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)

    def keyPressEvent(self, event):
        if self.is_drawing and event.key() == Qt.Key_Backspace:
            selected_items = self.scene().selectedItems()
            if selected_items and isinstance(selected_items[0], DraggablePointItem):
                if len(self.drawing_points) > 3:
                    index_to_delete = selected_items[0].index
                    self.drawing_points.pop(index_to_delete)
                    self.update_drawing_path()
                    self.update_point_items()
                    self.main_window.status.showMessage("Точка удалена. Правый клик для сохранения.")
                else:
                    self.main_window.status.showMessage("Нельзя удалить эту точку. Полигон должен иметь минимум 3 вершины.")
        else:
            super().keyPressEvent(event)

    def start_drawing_mode(self, initial_points=None):
        self.is_drawing = True
        self.drawing_points = initial_points if initial_points else []
        self.setDragMode(QGraphicsView.NoDrag)
        self.clear_drawing_items()

        red_pen = QPen(QColor(255, 0, 0), 2)
        semitransparent_blue = QBrush(QColor(0, 0, 255, 60))
        self.drawing_path_item = self.scene().addPath(QPainterPath(), red_pen, semitransparent_blue)
        self.update_drawing_path()
        self.update_point_items()

    def stop_drawing_mode(self):
        self.is_drawing = False
        self.drawing_points = []
        self.clear_drawing_items()
        self.setDragMode(QGraphicsView.ScrollHandDrag)

    def update_drawing_path(self):
        if not self.drawing_path_item:
            return
        path = QPainterPath()
        if self.drawing_points:
            path.moveTo(self.drawing_points[0])
            for p in self.drawing_points[1:]:
                path.lineTo(p)
            if len(self.drawing_points) > 1:
                path.lineTo(self.drawing_points[0])
        self.drawing_path_item.setPath(path)

    def update_point_items(self):
        self.clear_point_items()
        for i, p in enumerate(self.drawing_points):
            point_item = DraggablePointItem(p.x(), p.y(), 10, i)
            self.scene().addItem(point_item)
            point_item.point_moved.connect(self.handle_point_moved)
            self.point_items.append(point_item)

    def handle_point_moved(self, index, new_pos):
        if 0 <= index < len(self.drawing_points):
            self.drawing_points[index] = new_pos
            self.update_drawing_path()

    def clear_point_items(self):
        for item in self.point_items:
            self.scene().removeItem(item)
        self.point_items.clear()

    def clear_drawing_items(self):
        self.clear_point_items()
        if self.drawing_path_item:
            self.scene().removeItem(self.drawing_path_item)
            self.drawing_path_item = None

    def mousePressEvent(self, event):
        if self.is_drawing:
            if event.button() == Qt.LeftButton:
                scene_pos = self.mapToScene(event.pos())
                self.drawing_points.append(scene_pos)
                debug_log(f"Добавлена точка: ({scene_pos.x()}, {scene_pos.y()})")
                self.update_drawing_path()
                self.update_point_items()
            elif event.button() == Qt.RightButton:
                if len(self.drawing_points) > 2:
                    self.drawing_finished.emit(self.drawing_points)
                    self.is_drawing = False
                    self.drawing_points = []
                    self.clear_drawing_items()
                    self.setDragMode(QGraphicsView.ScrollHandDrag)
                else:
                    self.main_window.status.showMessage("Недостаточно точек для полигона. Попробуйте еще раз.")
        else:
            super().mousePressEvent(event)
