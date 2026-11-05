"""3D Viewport with SketchUp-style navigation."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QMouseEvent, QWheelEvent, QPainter, QColor, QFont
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from core.camera import Camera
from core.scene import Scene
from core.geometry import Mesh, Vertex, Edge, Face


class Viewport3D(QOpenGLWidget):
    """
    Основной 3D-холст.

    Управление (SketchUp-стиль):
    - Средняя кнопка + drag  → Orbit
    - Shift + Средняя + drag → Pan
    - Колёсико               → Zoom
    - Левая кнопка           → инструмент (пока просто выделение)
    """

    selection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

        self.camera = Camera()
        self.scene = Scene()

        # состояние мыши
        self._last_pos: Optional[QPoint] = None
        self._orbiting = False
        self._panning = False

        # текущий инструмент (позже будет объект Tool)
        self.current_tool = "select"

        # тестовая геометрия
        self.scene.create_test_box(size=2.0, center=(0, 1, 0))

    # ------------------------------------------------------------------
    # OpenGL lifecycle
    # ------------------------------------------------------------------
    def initializeGL(self):
        glClearColor(0.18, 0.18, 0.20, 1.0)  # тёмный фон как в SketchUp
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glLineWidth(1.5)

    def resizeGL(self, w: int, h: int):
        glViewport(0, 0, w, h)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        aspect = self.width() / max(self.height(), 1)
        self.camera.apply(aspect)

        # --- сетка и оси ---
        self._draw_grid()
        self._draw_axes()

        # --- геометрия сцены ---
        for mesh in self.scene.all_meshes():
            self._draw_mesh(mesh)

        # --- гизмо (пока простой) ---
        if self.scene.selected:
            self._draw_simple_gizmo()

        # оверлей (текст)
        self._draw_overlay()

    # ------------------------------------------------------------------
    # Рисование
    # ------------------------------------------------------------------
    def _draw_grid(self, size: float = 20.0, step: float = 1.0):
        glDisable(GL_DEPTH_TEST)
        glBegin(GL_LINES)

        # основная сетка
        glColor4f(0.35, 0.35, 0.38, 0.6)
        for i in range(int(-size), int(size) + 1):
            if i == 0:
                continue
            # линии вдоль X
            glVertex3f(i * step, 0, -size)
            glVertex3f(i * step, 0, size)
            # линии вдоль Z
            glVertex3f(-size, 0, i * step)
            glVertex3f(size, 0, i * step)

        # оси сетки (чуть ярче)
        glColor4f(0.55, 0.55, 0.58, 0.9)
        glVertex3f(-size, 0, 0)
        glVertex3f(size, 0, 0)
        glVertex3f(0, 0, -size)
        glVertex3f(0, 0, size)

        glEnd()
        glEnable(GL_DEPTH_TEST)

    def _draw_axes(self, length: float = 3.0):
        glDisable(GL_DEPTH_TEST)
        glLineWidth(2.5)
        glBegin(GL_LINES)

        # X — красный
        glColor3f(0.9, 0.25, 0.25)
        glVertex3f(0, 0, 0)
        glVertex3f(length, 0, 0)

        # Y — зелёный
        glColor3f(0.3, 0.85, 0.3)
        glVertex3f(0, 0, 0)
        glVertex3f(0, length, 0)

        # Z — синий
        glColor3f(0.3, 0.45, 0.95)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, length)

        glEnd()
        glLineWidth(1.5)
        glEnable(GL_DEPTH_TEST)

    def _draw_mesh(self, mesh: Mesh):
        # грани (полупрозрачные)
        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(1.0, 1.0)

        for face in mesh.faces:
            if face.selected:
                glColor4f(0.3, 0.6, 1.0, 0.45)
            else:
                glColor4f(0.55, 0.55, 0.58, 0.35)

            glBegin(GL_POLYGON)
            for v in face.vertices:
                glVertex3fv(v.position)
            glEnd()

        glDisable(GL_POLYGON_OFFSET_FILL)

        # рёбра
        glBegin(GL_LINES)
        for edge in mesh.edges:
            if edge.selected:
                glColor3f(1.0, 0.7, 0.15)
                glLineWidth(3.0)
            else:
                glColor3f(0.85, 0.85, 0.88)
                glLineWidth(1.5)
            p1, p2 = edge.points
            glVertex3fv(p1)
            glVertex3fv(p2)
        glEnd()

        # вершины
        glPointSize(7.0)
        glBegin(GL_POINTS)
        for v in mesh.vertices:
            if v.selected:
                glColor3f(1.0, 0.85, 0.2)
            else:
                glColor3f(0.95, 0.95, 0.98)
            glVertex3fv(v.position)
        glEnd()

    def _draw_simple_gizmo(self):
        """Временный простой гизмо в центре выделения."""
        # найдём центр
        centers = []
        for obj in self.scene.selected:
            if isinstance(obj, Mesh):
                centers.append(obj.center())
            elif isinstance(obj, Vertex):
                centers.append(obj.position)
        if not centers:
            return

        center = np.mean(centers, axis=0)
        size = 1.2

        glDisable(GL_DEPTH_TEST)
        glLineWidth(3.0)
        glBegin(GL_LINES)

        # X
        glColor3f(1.0, 0.2, 0.2)
        glVertex3fv(center)
        glVertex3f(center[0] + size, center[1], center[2])

        # Y
        glColor3f(0.2, 1.0, 0.2)
        glVertex3fv(center)
        glVertex3f(center[0], center[1] + size, center[2])

        # Z
        glColor3f(0.2, 0.4, 1.0)
        glVertex3fv(center)
        glVertex3f(center[0], center[1], center[2] + size)

        glEnd()
        glLineWidth(1.5)
        glEnable(GL_DEPTH_TEST)

    def _draw_overlay(self):
        """Текст поверх OpenGL (через QPainter)."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor(200, 200, 210))
        font = QFont("Segoe UI", 10)
        painter.setFont(font)

        info = (
            f"Tool: {self.current_tool}  |  "
            f"Dist: {self.camera.distance:.1f}  |  "
            f"Objects: {len(self.scene.root)}"
        )
        painter.drawText(12, 22, info)
        painter.drawText(12, self.height() - 12, "MMB Orbit  •  Shift+MMB Pan  •  Wheel Zoom")
        painter.end()

    # ------------------------------------------------------------------
    # События мыши (навигация)
    # ------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent):
        self._last_pos = event.position().toPoint()

        if event.button() == Qt.MiddleButton:
            if event.modifiers() & Qt.ShiftModifier:
                self._panning = True
            else:
                self._orbiting = True
            self.setCursor(Qt.ClosedHandCursor)

        elif event.button() == Qt.LeftButton:
            # пока простое выделение по клику (позже raycast)
            self._handle_select_click(event)

        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._last_pos is None:
            return

        pos = event.position().toPoint()
        dx = pos.x() - self._last_pos.x()
        dy = pos.y() - self._last_pos.y()

        if self._orbiting:
            self.camera.orbit(dx, dy)
            self.update()
        elif self._panning:
            self.camera.pan(dx, dy)
            self.update()

        self._last_pos = pos

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._orbiting = False
        self._panning = False
        self._last_pos = None
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y() / 120.0  # стандартные «щелчки»
        self.camera.zoom(delta)
        self.update()

    # ------------------------------------------------------------------
    # Простое выделение (заглушка)
    # ------------------------------------------------------------------
    def _handle_select_click(self, event: QMouseEvent):
        """Пока выделяем весь меш при клике (позже сделаем raycast)."""
        additive = bool(event.modifiers() & Qt.ControlModifier)

        # для демо — выделяем первый меш
        meshes = self.scene.all_meshes()
        if meshes:
            self.scene.select(meshes[0], additive=additive)
            self.selection_changed.emit()
