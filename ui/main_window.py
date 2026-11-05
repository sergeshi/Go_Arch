"""Главное окно приложения."""

from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QToolBar, QStatusBar, QLabel,
    QVBoxLayout, QWidget, QButtonGroup, QToolButton,
)

from .viewport import Viewport3D


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Go_Arch — Architectural Sketches & Blockouts")
        self.resize(1400, 900)

        # --- центральный виджет ---
        self.viewport = Viewport3D()
        self.setCentralWidget(self.viewport)

        # --- тулбар инструментов ---
        self._create_toolbar()

        # --- статусбар ---
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Готово. Средняя кнопка — Orbit, Shift+средняя — Pan, колёсико — Zoom")

        # связи
        self.viewport.selection_changed.connect(self._on_selection_changed)

    def _create_toolbar(self):
        toolbar = QToolBar("Tools")
        toolbar.setIconSize(QSize(28, 28))
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        tools = [
            ("select", "Выбор (V)", "V"),
            ("line", "Линия (L)", "L"),
            ("rect", "Прямоугольник (R)", "R"),
            ("circle", "Круг (C)", "C"),
            ("polygon", "Многоугольник (P)", "P"),
            ("arc", "Дуга (A)", "A"),
            ("move", "Перемещение (M)", "M"),
            ("rotate", "Поворот (Q)", "Q"),
            ("scale", "Масштаб (S)", "S"),
            ("extrude", "Выдавливание (E)", "E"),
        ]

        for name, tip, shortcut in tools:
            btn = QToolButton()
            btn.setText(name.capitalize())
            btn.setToolTip(f"{tip}")
            btn.setCheckable(True)
            btn.setProperty("tool_name", name)
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

        # кнопка «сбросить камеру»
        reset_btn = QToolButton()
        reset_btn.setText("Reset View")
        reset_btn.setToolTip("Сбросить камеру")
        reset_btn.clicked.connect(self._reset_camera)
        toolbar.addWidget(reset_btn)

    def _on_tool_button(self, btn: QToolButton):
        name = btn.property("tool_name")
        self._set_tool(name)

    def _set_tool(self, name: str):
        self.viewport.current_tool = name
        # синхронизируем кнопки
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
        self.status.showMessage(f"Выделено объектов: {n}")
