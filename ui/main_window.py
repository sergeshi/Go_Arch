"""Главное окно — тёмный интерфейс, вертикальная панель инструментов слева."""

from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QTimer, QObject, QEvent
from PySide6.QtGui import QAction, QKeySequence, QPalette, QColor, QHelpEvent
from PySide6.QtWidgets import (
    QMainWindow, QToolBar, QStatusBar, QButtonGroup, QToolButton,
    QApplication, QStyleFactory, QToolTip, QComboBox, QLabel, QWidget,
    QVBoxLayout, QHBoxLayout, QFrame, QSizePolicy, QCheckBox,
)

from .viewport import Viewport3D
from core.units import Unit


DARK_QSS = """
QMainWindow, QWidget {
    background-color: #2b2b2e;
    color: #e0e0e4;
    font-family: "Segoe UI", "Arial";
    font-size: 12px;
}
QToolBar {
    background-color: #232326;
    border: none;
    spacing: 3px;
    padding: 6px 4px;
}
QToolBar::separator {
    background-color: #3a3a3e;
    height: 1px;
    margin: 6px 4px;
}
QToolButton {
    background-color: transparent;
    color: #c8c8ce;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 8px 6px;
    min-width: 72px;
    min-height: 32px;
    text-align: center;
}
QToolButton:hover {
    background-color: #3a3a40;
    color: #ffffff;
    border: 1px solid #4a4a52;
}
QToolButton:checked {
    background-color: #3d5a80;
    color: #ffffff;
    border: 1px solid #5a7aa0;
}
QToolButton:pressed {
    background-color: #2f4a6a;
}
QStatusBar {
    background-color: #1e1e20;
    color: #a0a0a8;
    border-top: 1px solid #141416;
    font-size: 11px;
}
QStatusBar::item { border: none; }
QToolTip {
    background-color: #1a1a1c;
    color: #e8e8ec;
    border: 1px solid #4a4a52;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 12px;
}
QComboBox {
    background-color: #2a2a2e;
    color: #e0e0e4;
    border: 1px solid #3a3a40;
    border-radius: 4px;
    padding: 4px 8px;
    min-width: 64px;
}
QComboBox:hover { border: 1px solid #5a5a62; }
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView {
    background-color: #2a2a2e;
    color: #e0e0e4;
    selection-background-color: #3d5a80;
}
QCheckBox { color: #c8c8ce; spacing: 6px; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1px solid #4a4a52;
    border-radius: 3px;
    background: #2a2a2e;
}
QCheckBox::indicator:checked {
    background: #3d5a80;
    border-color: #5a7aa0;
}
QLabel { color: #a0a0a8; }
QFrame#LeftPanel {
    background-color: #232326;
    border-right: 1px solid #1a1a1c;
}
"""


class TooltipDelayFilter(QObject):
    def __init__(self, delay_ms: int = 1100):
        super().__init__()
        self.delay_ms = delay_ms
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._show)
        self._widget = None
        self._pos = None
        self._text = ""

    def eventFilter(self, obj, event):
        et = event.type()
        if et == QEvent.Type.ToolTip:
            if isinstance(event, QHelpEvent):
                self._widget = obj
                self._pos = event.globalPos()
                self._text = obj.toolTip() if hasattr(obj, "toolTip") else ""
                if self._text:
                    self._timer.start(self.delay_ms)
                return True
        elif et in (QEvent.Type.Leave, QEvent.Type.MouseButtonPress, QEvent.Type.Hide):
            self._timer.stop()
            QToolTip.hideText()
        return False

    def _show(self):
        if self._widget and self._text:
            QToolTip.showText(self._pos, self._text, self._widget)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Go_Arch")
        self.resize(1440, 900)

        app = QApplication.instance()
        app.setStyle(QStyleFactory.create("Fusion"))
        app.setStyleSheet(DARK_QSS)

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(43, 43, 46))
        palette.setColor(QPalette.WindowText, QColor(224, 224, 228))
        palette.setColor(QPalette.Base, QColor(30, 30, 32))
        palette.setColor(QPalette.AlternateBase, QColor(40, 40, 44))
        palette.setColor(QPalette.ToolTipBase, QColor(26, 26, 28))
        palette.setColor(QPalette.ToolTipText, QColor(232, 232, 236))
        palette.setColor(QPalette.Text, QColor(224, 224, 228))
        palette.setColor(QPalette.Button, QColor(50, 50, 54))
        palette.setColor(QPalette.ButtonText, QColor(220, 220, 224))
        palette.setColor(QPalette.Highlight, QColor(61, 90, 128))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        app.setPalette(palette)

        # --- центральная область: левая панель + вьюпорт ---
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.left_panel = self._create_left_panel()
        layout.addWidget(self.left_panel)

        self.viewport = Viewport3D()
        layout.addWidget(self.viewport, stretch=1)

        self.setCentralWidget(central)

        # статусбар
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage(
            "Средняя кнопка — Orbit  ·  Shift+средняя / Shift+колёсико — Pan  ·  Колёсико — Zoom"
        )

        self.viewport.selection_changed.connect(self._on_selection_changed)
        self.viewport.status_message.connect(self.status.showMessage)

        # tooltips delay
        self._tip_filter = TooltipDelayFilter(1100)
        for btn in self.tool_group.buttons():
            btn.installEventFilter(self._tip_filter)

    def _create_left_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("LeftPanel")
        panel.setFixedWidth(96)

        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(4, 8, 4, 8)
        vbox.setSpacing(4)

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        tools = [
            ("select",  "Выбор  (V)\nВыделение объектов, точек, рёбер и граней", "V"),
            ("line",    "Линия  (L)\nРисование отрезков", "L"),
            ("rect",    "Прямоугольник  (R)\nРисование прямоугольников", "R"),
            ("circle",  "Круг  (C)\nРисование окружностей", "C"),
            ("polygon", "Многоугольник  (P)\n[ ] — число сторон", "P"),
            ("arc",     "Дуга  (A)\nТри точки: начало, конец, точка на дуге", "A"),
            ("move",    "Перемещение  (M)\nС привязкой к сетке и осям", "M"),
            ("rotate",  "Поворот  (Q)\nВокруг вертикальной оси, шаг 15°", "Q"),
            ("scale",   "Масштаб  (S)\nРавномерное масштабирование", "S"),
            ("extrude", "Выдавливание  (E)\nPush/Pull грани", "E"),
        ]

        for name, tip, shortcut in tools:
            btn = QToolButton()
            btn.setText(name.capitalize())
            btn.setToolTip(tip)
            btn.setCheckable(True)
            btn.setProperty("tool_name", name)
            btn.setAutoRaise(True)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            if name == "select":
                btn.setChecked(True)
            self.tool_group.addButton(btn)
            vbox.addWidget(btn)

            act = QAction(self)
            act.setShortcut(QKeySequence(shortcut))
            act.triggered.connect(lambda checked=False, n=name: self._set_tool(n))
            self.addAction(act)

        self.tool_group.buttonClicked.connect(self._on_tool_button)

        vbox.addSpacing(12)

        # --- единицы ---
        unit_label = QLabel("Единицы")
        unit_label.setAlignment(Qt.AlignCenter)
        vbox.addWidget(unit_label)

        self.unit_combo = QComboBox()
        self.unit_combo.addItem("mm", Unit.MM)
        self.unit_combo.addItem("cm", Unit.CM)
        self.unit_combo.addItem("m", Unit.M)
        self.unit_combo.setCurrentIndex(1)  # cm
        self.unit_combo.currentIndexChanged.connect(self._on_unit_changed)
        vbox.addWidget(self.unit_combo)

        vbox.addSpacing(8)

        # --- snap ---
        self.snap_check = QCheckBox("Snap")
        self.snap_check.setChecked(True)
        self.snap_check.setToolTip("Привязка к сетке, вершинам, осям")
        self.snap_check.toggled.connect(self._on_snap_toggled)
        vbox.addWidget(self.snap_check)

        self.grid_combo = QComboBox()
        for label, meters in [("1 mm", 0.001), ("5 mm", 0.005), ("1 cm", 0.01),
                              ("5 cm", 0.05), ("10 cm", 0.1), ("50 cm", 0.5), ("1 m", 1.0)]:
            self.grid_combo.addItem(label, meters)
        self.grid_combo.setCurrentIndex(4)  # 10 cm
        self.grid_combo.setToolTip("Шаг сетки / привязки")
        self.grid_combo.currentIndexChanged.connect(self._on_grid_changed)
        vbox.addWidget(self.grid_combo)

        vbox.addSpacing(12)

        reset_btn = QToolButton()
        reset_btn.setText("Reset")
        reset_btn.setToolTip("Сбросить камеру")
        reset_btn.setAutoRaise(True)
        reset_btn.clicked.connect(self._reset_camera)
        vbox.addWidget(reset_btn)

        vbox.addStretch(1)
        return panel

    def _on_tool_button(self, btn: QToolButton):
        self._set_tool(btn.property("tool_name"))

    def _set_tool(self, name: str):
        self.viewport.set_tool(name)
        for btn in self.tool_group.buttons():
            if btn.property("tool_name") == name:
                btn.setChecked(True)
                break

    def _on_unit_changed(self, index: int):
        unit = self.unit_combo.itemData(index)
        if unit is not None:
            self.viewport.units.set_unit(unit)
            self.viewport.update()
            self.status.showMessage(f"Единицы: {unit.value}")

    def _on_snap_toggled(self, checked: bool):
        self.viewport.snap.enabled = checked
        self.viewport.update()

    def _on_grid_changed(self, index: int):
        size = self.grid_combo.itemData(index)
        if size is not None:
            self.viewport.snap.set_grid_size(float(size))
            self.viewport.update()
            self.status.showMessage(f"Шаг привязки: {self.grid_combo.currentText()}")

    def _reset_camera(self):
        self.viewport.camera.distance = 12.0
        self.viewport.camera.yaw = 45.0
        self.viewport.camera.pitch = 30.0
        self.viewport.camera.target[:] = [0.0, 0.0, 0.0]
        self.viewport.update()
        self.status.showMessage("Камера сброшена")

    def _on_selection_changed(self):
        n = len(self.viewport.scene.selected)
        self.status.showMessage(f"Выделено: {n}")
