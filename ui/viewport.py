"""3D Viewport with SketchUp-style navigation and tools."""

from __future__ import annotations

from typing import Optional, Dict, Tuple
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QMouseEvent, QWheelEvent, QPainter, QColor, QFont, QKeyEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from core.camera import Camera
from core.scene import Scene
from core.geometry import Mesh, Vertex, Edge, Face
from core.units import UnitSystem, Unit
from core.snap import SnapSystem
from tools import TOOL_CLASSES


class Viewport3D(QOpenGLWidget):
    selection_changed = Signal()
    status_message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

        self.camera = Camera()
        self.scene = Scene()
        self.units = UnitSystem(Unit.CM)
        self.snap = SnapSystem()
        self.snap.grid_size = 0.1  # 10 cm

        self._last_pos: Optional[QPoint] = None
        self._orbiting = False
        self._panning = False

        self.tools: Dict[str, object] = {}
        self.current_tool_name = "select"
        self.current_tool = None

        for name, cls in TOOL_CLASSES.items():
            self.tools[name] = cls(self)
        self.set_tool("select")

        self.scene.create_test_box(size=2.0, center=(0, 1, 0))

        # курсор на земле (для отладки / превью)
        self.cursor_world: Optional[np.ndarray] = None

    def set_tool(self, name: str):
        if self.current_tool:
            self.current_tool.deactivate()
        self.current_tool_name = name
        self.current_tool = self.tools.get(name)
        if self.current_tool:
            self.current_tool.activate()
        self.setFocus()
        self._emit_status()
        self.update()

    def _emit_status(self):
        if self.current_tool:
            self.status_message.emit(self.current_tool.status_text())

    # ------------------------------------------------------------------
    # Ray casting
    # ------------------------------------------------------------------
    def _camera_basis(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """eye, forward, right, up"""
        eye = self.camera.position()
        target = np.asarray(self.camera.target, dtype=np.float64)
        forward = target - eye
        fl = np.linalg.norm(forward)
        if fl < 1e-12:
            forward = np.array([0.0, 0.0, -1.0])
        else:
            forward = forward / fl

        world_up = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        # если смотрим почти вертикально — другой up
        if abs(np.dot(forward, world_up)) > 0.999:
            world_up = np.array([0.0, 0.0, 1.0], dtype=np.float64)

        right = np.cross(forward, world_up)
        right = right / (np.linalg.norm(right) + 1e-12)
        up = np.cross(right, forward)
        up = up / (np.linalg.norm(up) + 1e-12)
        return eye, forward, right, up

    def screen_to_ray(self, x: float, y: float) -> Tuple[np.ndarray, np.ndarray]:
        """Возвращает (origin, direction) луча из пикселя."""
        w = max(self.width(), 1)
        h = max(self.height(), 1)

        # NDC [-1, 1], Y вверх
        nx = (2.0 * x) / w - 1.0
        ny = 1.0 - (2.0 * y) / h

        aspect = w / float(h)
        fov_rad = np.radians(self.camera.fov)
        tan_half = np.tan(fov_rad * 0.5)

        # В view-space камера смотрит вдоль -Z.
        # view X → right, view Y → up, view -Z → forward (направление взгляда)
        dir_view = np.array([
            nx * tan_half * aspect,
            ny * tan_half,
            -1.0,
        ], dtype=np.float64)

        eye, forward, right, up = self._camera_basis()

        # Правильный переход view → world:
        # dir_world = right*vx + up*vy + forward*(-vz)
        ray_dir = right * dir_view[0] + up * dir_view[1] + forward * (-dir_view[2])
        ray_dir = ray_dir / (np.linalg.norm(ray_dir) + 1e-12)
        return eye, ray_dir

    def screen_to_world(self, x: float, y: float, plane_y: float = 0.0) -> Optional[np.ndarray]:
        """Пересечение луча с горизонтальной плоскостью y = plane_y."""
        eye, ray_dir = self.screen_to_ray(x, y)

        if abs(ray_dir[1]) < 1e-10:
            # луч параллелен плоскости — берём точку на луче на расстоянии distance
            return eye + ray_dir * self.camera.distance

        t = (plane_y - eye[1]) / ray_dir[1]
        # допускаем небольшое отрицательное (камера чуть ниже плоскости)
        if t < -0.01:
            # луч уходит от плоскости — fallback: проекция target на плоскость + смещение по экрану
            t = abs(t)

        pt = eye + ray_dir * t
        return pt

    def _event_world_pos(self, event) -> Optional[np.ndarray]:
        pos = event.position()
        plane_y = 0.0
        tool = self.current_tool
        if tool is not None:
            if getattr(tool, "points", None):
                plane_y = float(tool.points[-1][1])
            elif getattr(tool, "p1", None) is not None:
                plane_y = float(tool.p1[1])
            elif getattr(tool, "center", None) is not None:
                plane_y = float(tool.center[1])
            elif getattr(tool, "start", None) is not None:
                plane_y = float(tool.start[1])
        return self.screen_to_world(pos.x(), pos.y(), plane_y=plane_y)

    # ------------------------------------------------------------------
    # OpenGL
    # ------------------------------------------------------------------
    def initializeGL(self):
        glClearColor(0.16, 0.16, 0.18, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_POINT_SMOOTH)
        glLineWidth(1.5)

    def resizeGL(self, w: int, h: int):
        glViewport(0, 0, w, h)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        aspect = self.width() / max(self.height(), 1)
        self.camera.apply(aspect)

        self._draw_grid()
        self._draw_axes()

        for mesh in self.scene.all_meshes():
            self._draw_mesh(mesh)

        if self.scene.selected:
            self._draw_simple_gizmo()

        if self.current_tool:
            self.current_tool.draw_preview()

        # курсор привязки
        if self.cursor_world is not None:
            self._draw_cursor(self.cursor_world)

        self._draw_overlay()

    def _draw_cursor(self, p: np.ndarray):
        glDisable(GL_DEPTH_TEST)
        glPointSize(12.0)
        glBegin(GL_POINTS)
        glColor3f(1.0, 0.4, 0.2)
        glVertex3fv(p.astype(np.float32))
        glEnd()
        # крестик
        s = max(self.snap.grid_size * 0.5, 0.05)
        glLineWidth(1.5)
        glColor3f(1.0, 0.5, 0.2)
        glBegin(GL_LINES)
        glVertex3f(p[0] - s, p[1], p[2])
        glVertex3f(p[0] + s, p[1], p[2])
        glVertex3f(p[0], p[1], p[2] - s)
        glVertex3f(p[0], p[1], p[2] + s)
        glEnd()
        glEnable(GL_DEPTH_TEST)

    def _draw_grid(self, size: float = 20.0, step: float = 1.0):
        glDisable(GL_DEPTH_TEST)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        glColor4f(0.32, 0.32, 0.35, 0.55)
        for i in range(int(-size), int(size) + 1):
            if i == 0:
                continue
            glVertex3f(i * step, 0, -size)
            glVertex3f(i * step, 0, size)
            glVertex3f(-size, 0, i * step)
            glVertex3f(size, 0, i * step)
        glColor4f(0.48, 0.48, 0.52, 0.85)
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
        glColor3f(0.92, 0.28, 0.28)
        glVertex3f(0, 0, 0)
        glVertex3f(length, 0, 0)
        glColor3f(0.28, 0.82, 0.32)
        glVertex3f(0, 0, 0)
        glVertex3f(0, length, 0)
        glColor3f(0.28, 0.48, 0.95)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, length)
        glEnd()
        glLineWidth(1.5)
        glEnable(GL_DEPTH_TEST)

    def _draw_mesh(self, mesh: Mesh):
        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(1.0, 1.0)
        for face in mesh.faces:
            if face.selected or mesh.selected:
                glColor4f(0.25, 0.55, 0.95, 0.42)
            else:
                glColor4f(0.50, 0.50, 0.54, 0.32)
            glBegin(GL_POLYGON)
            for v in face.vertices:
                glVertex3fv(v.position.astype(np.float32))
            glEnd()
        glDisable(GL_POLYGON_OFFSET_FILL)

        glLineWidth(1.5)
        glColor3f(0.82, 0.82, 0.86)
        glBegin(GL_LINES)
        for edge in mesh.edges:
            if not edge.selected:
                p1, p2 = edge.points
                glVertex3fv(p1.astype(np.float32))
                glVertex3fv(p2.astype(np.float32))
        glEnd()

        glLineWidth(3.0)
        glColor3f(1.0, 0.72, 0.18)
        glBegin(GL_LINES)
        for edge in mesh.edges:
            if edge.selected:
                p1, p2 = edge.points
                glVertex3fv(p1.astype(np.float32))
                glVertex3fv(p2.astype(np.float32))
        glEnd()
        glLineWidth(1.5)

        glPointSize(7.0)
        glBegin(GL_POINTS)
        for v in mesh.vertices:
            if v.selected:
                glColor3f(1.0, 0.85, 0.2)
            else:
                glColor3f(0.93, 0.93, 0.96)
            glVertex3fv(v.position.astype(np.float32))
        glEnd()

    def _draw_simple_gizmo(self):
        centers = []
        for obj in self.scene.selected:
            if isinstance(obj, Mesh):
                centers.append(obj.center())
            elif isinstance(obj, Vertex):
                centers.append(obj.position)
            elif isinstance(obj, Face):
                centers.append(np.mean([v.position for v in obj.vertices], axis=0))
        if not centers:
            return
        center = np.mean(centers, axis=0)
        size = 1.2
        glDisable(GL_DEPTH_TEST)
        glLineWidth(3.0)
        glBegin(GL_LINES)
        glColor3f(1.0, 0.2, 0.2)
        glVertex3fv(center.astype(np.float32))
        glVertex3f(center[0] + size, center[1], center[2])
        glColor3f(0.2, 1.0, 0.2)
        glVertex3fv(center.astype(np.float32))
        glVertex3f(center[0], center[1] + size, center[2])
        glColor3f(0.2, 0.4, 1.0)
        glVertex3fv(center.astype(np.float32))
        glVertex3f(center[0], center[1], center[2] + size)
        glEnd()
        glLineWidth(1.5)
        glEnable(GL_DEPTH_TEST)

    def _draw_overlay(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor(180, 180, 190))
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        unit = self.units.unit.value
        snap = "ON" if self.snap.enabled else "OFF"
        info = f"{self.current_tool_name.upper()}  ·  {unit}  ·  snap {snap}  ·  grid {self.units.format(self.snap.grid_size)}"
        painter.drawText(12, 20, info)
        if self.cursor_world is not None:
            p = self.cursor_world
            painter.drawText(
                12, 38,
                f"xyz  {self.units.format(p[0])}  {self.units.format(p[1])}  {self.units.format(p[2])}"
            )
        painter.drawText(
            12, self.height() - 10,
            "MMB Orbit  ·  Shift+MMB / Shift+Wheel Pan  ·  Wheel Zoom"
        )
        painter.end()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent):
        self.setFocus()
        self._last_pos = event.position().toPoint()

        if event.button() == Qt.MiddleButton:
            if event.modifiers() & Qt.ShiftModifier:
                self._panning = True
            else:
                self._orbiting = True
            self.setCursor(Qt.ClosedHandCursor)
            return

        if event.button() == Qt.LeftButton and self.current_tool:
            world = self._event_world_pos(event)
            if world is not None:
                # snap для отображения курсора
                last = None
                tool = self.current_tool
                if getattr(tool, "points", None):
                    last = tool.points[-1]
                elif getattr(tool, "p1", None) is not None:
                    last = tool.p1
                elif getattr(tool, "center", None) is not None:
                    last = tool.center
                snapped = self.snap.snap_point(world, self.scene, last_point=last)
                self.cursor_world = snapped.point
            self.current_tool.on_mouse_press(event, world)
            self._emit_status()

        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position().toPoint()

        if self._orbiting or self._panning:
            if self._last_pos is not None:
                dx = pos.x() - self._last_pos.x()
                dy = pos.y() - self._last_pos.y()
                if self._orbiting:
                    self.camera.orbit(dx, dy)
                else:
                    self.camera.pan(dx, dy)
                self.update()
            self._last_pos = pos
            return

        world = self._event_world_pos(event)
        if world is not None:
            last = None
            tool = self.current_tool
            if tool is not None:
                if getattr(tool, "points", None):
                    last = tool.points[-1]
                elif getattr(tool, "p1", None) is not None:
                    last = tool.p1
                elif getattr(tool, "center", None) is not None:
                    last = tool.center
                elif getattr(tool, "start", None) is not None:
                    last = tool.start
            snapped = self.snap.snap_point(world, self.scene, last_point=last)
            self.cursor_world = snapped.point
            if self.current_tool:
                self.current_tool.on_mouse_move(event, snapped.point)
                self._emit_status()
        else:
            self.cursor_world = None

        self._last_pos = pos
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._orbiting = False
        self._panning = False
        self._last_pos = None
        self.setCursor(Qt.ArrowCursor)

        if self.current_tool and event.button() == Qt.LeftButton:
            world = self._event_world_pos(event)
            self.current_tool.on_mouse_release(event, world)
            self._emit_status()
        self.update()

    def wheelEvent(self, event: QWheelEvent):
        delta_y = event.angleDelta().y() / 120.0
        delta_x = event.angleDelta().x() / 120.0
        if event.modifiers() & Qt.ShiftModifier:
            self.camera.pan(-delta_x * 40.0, -delta_y * 40.0)
        else:
            self.camera.zoom(delta_y)
        self.update()

    def keyPressEvent(self, event: QKeyEvent):
        if self.current_tool:
            self.current_tool.on_key_press(event)
            self._emit_status()
        self.update()
