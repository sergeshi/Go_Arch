"""Главное окно приложения — тёмный интерфейс в духе SketchUp."""

from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QAction, QKeySequence, QPalette, QColor, QFont
from PySide6.QtWidgets import (
    QMainWindow, QToolBar, QStatusBar, QLabel,
    QButtonGroup, QToolButton, QApplication, QStyleFactory,
    QWidget, QHBoxLayout, QSizePolicy,
)

from .viewport import Viewport3D


# ---------------------------------------------------------------------------
# Тёмная тема (близко к SketchUp / современных CAD)
# ---------------------------------------------------------------------------
DARK_QSS = """
/* Общий фон */
QMainWindow, QWidget {
    background-color: #2b2b2e;
    color: #e0e0e4;
    font-family: "Segoe UI", "Arial";
    font-size: 12px;
}

/* Тулбар */
QToolBar {
    background-color: #232326;
    border: none;
    border-bottom: 1px solid #1a1a1c;
    spacing: 2px;
    padding: 4px 6px;
}

QToolBar::separator {
    background-color: #3a3a3e;
    width: 1px;
    margin: 6px 4px;
}

/* Кнопки инструментов */
QToolButton {
    background-color: transparent;
    color: #c8c8ce;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 6px 10px;
    min-width: 52px;
    min-height: 28px;
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

/* Статусбар */
QStatusBar {
    background-color: #1e1e20;
    color: #a0a0a8;
    border-top: 1px solid #141416;
    font-size: 11px;
}

QStatusBar::item {
    border: none;
}

/* Подсказки */
QToolTip {
    background-color: #1a1a1c;
    color: #e8e8ec;
    border: 1px solid #4a4a52;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 12px;
}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Go_Arch")
        self.resize(1440, 900)

        # тёмная тема
        self.setStyleSheet(DARK_QSS)

        # задержка подсказки > 1 секунды
        QApplication.instance().setStyleSheet(DARK_QSS)  # чтобы QToolTip тоже подхватил
        # Qt использует style hint; принудительно увеличиваем задержку
        from PySide6.QtWidgets import QStyle
        # через event filter / timer сделаем позже; пока ставим через style
        app = QApplication.instance()
        app.setStyle(QStyleFactory.create("Fusion"))

        # палитра Fusion тёмная
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

        # --- центральный виджет ---
        self.viewport = Viewport3D()
        self.setCentralWidget(self.viewport)

        # --- тулбар инструментов ---
        self._create_toolbar()

        # --- статусбар ---
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage(
            "Средняя кнопка — Orbit  ·  Shift+средняя / Shift+колёсико — Pan  ·  Колёсико — Zoom"
        )

        # связи
        self.viewport.selection_changed.connect(self._on_selection_changed)

        # Увеличиваем задержку появления подсказок (~1100 мс)
        # Qt не даёт прямого API, поэтому ставим через style hint + небольшой хак
        self._setup_tooltip_delay()

    def _setup_tooltip_delay(self):
        """Делаем появление tooltip примерно через 1+ секунду."""
        # В Qt задержка tooltip контролируется через QStyle.SH_ToolTip_WakeUpDelay
        # (миллисекунды). Мы переопределяем через proxy style было бы идеально,
        # но для простоты используем глобальный таймер + event filter позже.
        # Пока ставим максимально возможное через stylesheet + надеемся на систему.
        # Более надёжный способ — свой eventFilter.
        from PySide6.QtCore import QObject, QEvent

        class TooltipDelayFilter(QObject):
            def __init__(self, delay_ms=1100):
                super().__init__()
                self.delay_ms = delay_ms
                self._timer = QTimer()
                self._timer.setSingleShot(True)
                self._widget = None
                self._pos = None
                self._text = ""

            def eventFilter(self, obj, event):
                if event.type() == QEvent.ToolTip:
                    # перехватываем и показываем сами с задержкой
                    from PySide6.QtGui import QHelpEvent
                    from PySide6.QtWidgets import QToolTip
                    if isinstance(event, QHelpEvent):
                        self._widget = obj
                        self._pos = event.globalPos()
                        self._text = obj.toolTip() if hasattr(obj, "toolTip") else ""
                        if self._text:
                            self._timer.stop()
                            self._timer.timeout.connect(self._show)
                            self._timer.start(self.delay_ms)
                        return True  # блокируем стандартный tooltip
                elif event.type() in (QEvent.Leave, QEvent.MouseButtonPress):
                    self._timer.stop()
                    from PySide6.QtWidgets import QToolTip
                    QToolTip.hideText()
                return False

            def _show(self):
                from PySide6.QtWidgets import QToolTip
                if self._widget and self._text:
                    QToolTip.showText(self._pos, self._text, self._widget)

        self._tip_filter = TooltipDelayFilter(1100)
        # ставим фильтр на все кнопки тулбара
        for btn in self.tool_group.buttons():
            btn.installEventFilter(self._tip_filter)
            # также на reset
        # (reset добавим отдельно если нужно)

    def _create_toolbar(self):
        toolbar = QToolBar("Tools")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)  # пока текст, потом иконки
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        # name, tooltip (с горячей клавишей), shortcut
        tools = [
            ("select",  "Выбор  (V)\nВыделение объектов, точек, рёбер и граней", "V"),
            ("line",    "Линия  (L)\nРисование отрезков", "L"),
            ("rect",    "Прямоугольник  (R)\nРисование прямоугольников", "R"),
            ("circle",  "Круг  (C)\nРисование окружностей", "C"),
            ("polygon", "Многоугольник  (P)\nРисование правильных многоугольников", "P"),
            ("arc",     "Дуга  (A)\nРисование дуг", "A"),
            ("move",    "Перемещение  (M)\nПеремещение выделенного", "M"),
            ("rotate",  "Поворот  (Q)\nВращение выделенного", "Q"),
            ("scale",   "Масштаб  (S)\nМасштабирование выделенного", "S"),
            ("extrude", "Выдавливание  (E)\nPush/Pull — выдавливание граней", "E"),
        ]

        for name, tip, shortcut in tools:
            btn = QToolButton()
            btn.setText(name.capitalize())
            btn.setToolTip(tip)
            btn.setCheckable(True)
            btn.setProperty("tool_name", name)
            btn.setAutoRaise(True)
            if name == "select":
                btn.setChecked(True)
            self.tool_group.addButton(btn)
            toolbar.addWidget(btn)

            # горячая клавиша
            act = QAction(self)
            act.setShortcut(QKeySequence(shortcut))
            act.triggered.connect(lambda checked=False, n=name: self._set_tool(n))
            self.addAction(act)

        self.tool_group.buttonClicked.connect(self._on_tool_button)

        toolbar.addSeparator()

        # кнопка сброса камеры
        reset_btn = QToolButton()
        reset_btn.setText("Reset")
        reset_btn.setToolTip("Сбросить камеру\nВернуть вид по умолчанию")
        reset_btn.setAutoRaise(True)
        reset_btn.clicked.connect(self._reset_camera)
        toolbar.addWidget(reset_btn)
        self._reset_btn = reset_btn

    def _on_tool_button(self, btn: QToolButton):
        name = btn.property("tool_name")
        self._set_tool(name)

    def _set_tool(self, name: str):
        self.viewport.current_tool = name
        for btn in self.tool_group.buttons():
            if btn.property("tool_name") == name:
                btn.setChecked(True)
                break
        self.status.showMessage(f"Инструмент: {name}")
        self.viewport.update()

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
