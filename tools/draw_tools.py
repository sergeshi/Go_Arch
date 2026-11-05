"""Инструменты рисования: линия, прямоугольник, круг, многоугольник, дуга."""

from __future__ import annotations

from typing import Optional, List
import math
import numpy as np
from OpenGL.GL import *
from PySide6.QtCore import Qt

from .base import Tool
from core.geometry import Mesh, Vertex


def _ground_or_point(world_pos: Optional[np.ndarray]) -> Optional[np.ndarray]:
    if world_pos is None:
        return None
    return world_pos.copy()


class LineTool(Tool):
    name = "line"
    label = "Линия"

    def __init__(self, viewport):
        super().__init__(viewport)
        self.points: List[np.ndarray] = []
        self.preview: Optional[np.ndarray] = None
        self.current_mesh: Optional[Mesh] = None

    def on_activate(self):
        self.points.clear()
        self.preview = None
        self.current_mesh = None

    def on_deactivate(self):
        self.points.clear()
        self.preview = None

    def on_mouse_press(self, event, world_pos):
        if event.button() != Qt.LeftButton or world_pos is None:
            return

        last = self.points[-1] if self.points else None
        snap = self.snap.snap_point(world_pos, self.scene, last_point=last)
        pt = snap.point

        self.points.append(pt)

        if self.current_mesh is None:
            self.current_mesh = Mesh(name="Lines")
            self.scene.add_mesh(self.current_mesh)

        if len(self.points) >= 2:
            v1 = self.current_mesh.add_vertex(self.points[-2])
            v2 = self.current_mesh.add_vertex(self.points[-1])
            self.current_mesh.add_edge(v1, v2)

        self.vp.update()

    def on_mouse_move(self, event, world_pos):
        if world_pos is None:
            return
        last = self.points[-1] if self.points else None
        snap = self.snap.snap_point(world_pos, self.scene, last_point=last)
        self.preview = snap.point
        self.vp.update()

    def on_key_press(self, event):
        if event.key() == Qt.Key_Escape:
            self.points.clear()
            self.preview = None
            self.current_mesh = None
            self.vp.update()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.points.clear()
            self.preview = None
            self.current_mesh = None
            self.vp.update()

    def draw_preview(self):
        if not self.points and self.preview is None:
            return

        glDisable(GL_DEPTH_TEST)
        glLineWidth(2.0)
        glColor3f(0.3, 0.85, 1.0)

        if len(self.points) >= 1 and self.preview is not None:
            glBegin(GL_LINES)
            p = self.points[-1]
            glVertex3fv(p.astype(np.float32))
            glVertex3fv(self.preview.astype(np.float32))
            glEnd()

        # точки
        glPointSize(8.0)
        glBegin(GL_POINTS)
        glColor3f(1.0, 0.9, 0.2)
        for p in self.points:
            glVertex3fv(p.astype(np.float32))
        if self.preview is not None:
            glColor3f(0.4, 0.9, 1.0)
            glVertex3fv(self.preview.astype(np.float32))
        glEnd()

        glEnable(GL_DEPTH_TEST)
        glLineWidth(1.5)

    def status_text(self) -> str:
        n = len(self.points)
        if n == 0:
            return "Линия: кликните первую точку"
        return f"Линия: точек {n}  ·  Esc — отмена  ·  Enter — закончить"


class RectTool(Tool):
    name = "rect"
    label = "Прямоугольник"

    def __init__(self, viewport):
        super().__init__(viewport)
        self.p1: Optional[np.ndarray] = None
        self.preview: Optional[np.ndarray] = None

    def on_activate(self):
        self.p1 = None
        self.preview = None

    def on_mouse_press(self, event, world_pos):
        if event.button() != Qt.LeftButton or world_pos is None:
            return

        snap = self.snap.snap_point(world_pos, self.scene, last_point=self.p1)
        pt = snap.point

        if self.p1 is None:
            self.p1 = pt
        else:
            self._create_rect(self.p1, pt)
            self.p1 = None
            self.preview = None
        self.vp.update()

    def on_mouse_move(self, event, world_pos):
        if self.p1 is None or world_pos is None:
            return
        snap = self.snap.snap_point(world_pos, self.scene, last_point=self.p1)
        self.preview = snap.point
        self.vp.update()

    def on_key_press(self, event):
        if event.key() == Qt.Key_Escape:
            self.p1 = None
            self.preview = None
            self.vp.update()

    def _create_rect(self, a: np.ndarray, b: np.ndarray):
        # прямоугольник на плоскости XZ (Y = a.y)
        y = a[1]
        x0, z0 = a[0], a[2]
        x1, z1 = b[0], b[2]

        mesh = Mesh(name="Rectangle")
        v0 = mesh.add_vertex([x0, y, z0])
        v1 = mesh.add_vertex([x1, y, z0])
        v2 = mesh.add_vertex([x1, y, z1])
        v3 = mesh.add_vertex([x0, y, z1])

        mesh.add_edge(v0, v1)
        mesh.add_edge(v1, v2)
        mesh.add_edge(v2, v3)
        mesh.add_edge(v3, v0)
        mesh.add_face([v0, v1, v2, v3])

        self.scene.add_mesh(mesh)

    def draw_preview(self):
        if self.p1 is None or self.preview is None:
            return
        a, b = self.p1, self.preview
        y = a[1]
        pts = [
            [a[0], y, a[2]],
            [b[0], y, a[2]],
            [b[0], y, b[2]],
            [a[0], y, b[2]],
        ]
        glDisable(GL_DEPTH_TEST)
        glLineWidth(2.0)
        glColor3f(0.3, 0.85, 1.0)
        glBegin(GL_LINE_LOOP)
        for p in pts:
            glVertex3fv(np.array(p, dtype=np.float32))
        glEnd()
        glEnable(GL_DEPTH_TEST)

    def status_text(self) -> str:
        if self.p1 is None:
            return "Прямоугольник: кликните первый угол"
        return "Прямоугольник: кликните противоположный угол  ·  Esc — отмена"


class CircleTool(Tool):
    name = "circle"
    label = "Круг"

    def __init__(self, viewport):
        super().__init__(viewport)
        self.center: Optional[np.ndarray] = None
        self.preview: Optional[np.ndarray] = None
        self.segments = 32

    def on_activate(self):
        self.center = None
        self.preview = None

    def on_mouse_press(self, event, world_pos):
        if event.button() != Qt.LeftButton or world_pos is None:
            return
        snap = self.snap.snap_point(world_pos, self.scene, last_point=self.center)
        pt = snap.point

        if self.center is None:
            self.center = pt
        else:
            radius = np.linalg.norm(pt - self.center)
            if radius > 1e-6:
                self._create_circle(self.center, radius)
            self.center = None
            self.preview = None
        self.vp.update()

    def on_mouse_move(self, event, world_pos):
        if self.center is None or world_pos is None:
            return
        snap = self.snap.snap_point(world_pos, self.scene, last_point=self.center)
        self.preview = snap.point
        self.vp.update()

    def on_key_press(self, event):
        if event.key() == Qt.Key_Escape:
            self.center = None
            self.preview = None
            self.vp.update()

    def _create_circle(self, center: np.ndarray, radius: float):
        mesh = Mesh(name="Circle")
        verts = []
        for i in range(self.segments):
            a = 2 * math.pi * i / self.segments
            x = center[0] + radius * math.cos(a)
            z = center[2] + radius * math.sin(a)
            verts.append(mesh.add_vertex([x, center[1], z]))

        for i in range(self.segments):
            mesh.add_edge(verts[i], verts[(i + 1) % self.segments])
        mesh.add_face(verts)
        self.scene.add_mesh(mesh)

    def draw_preview(self):
        if self.center is None or self.preview is None:
            return
        radius = np.linalg.norm(self.preview - self.center)
        glDisable(GL_DEPTH_TEST)
        glLineWidth(2.0)
        glColor3f(0.3, 0.85, 1.0)
        glBegin(GL_LINE_LOOP)
        for i in range(self.segments):
            a = 2 * math.pi * i / self.segments
            x = self.center[0] + radius * math.cos(a)
            z = self.center[2] + radius * math.sin(a)
            glVertex3f(x, self.center[1], z)
        glEnd()
        # радиус
        glBegin(GL_LINES)
        glVertex3fv(self.center.astype(np.float32))
        glVertex3fv(self.preview.astype(np.float32))
        glEnd()
        glEnable(GL_DEPTH_TEST)

    def status_text(self) -> str:
        if self.center is None:
            return "Круг: кликните центр"
        return "Круг: кликните точку на окружности  ·  Esc — отмена"


class PolygonTool(Tool):
    name = "polygon"
    label = "Многоугольник"

    def __init__(self, viewport):
        super().__init__(viewport)
        self.center: Optional[np.ndarray] = None
        self.preview: Optional[np.ndarray] = None
        self.sides = 6

    def on_activate(self):
        self.center = None
        self.preview = None

    def on_mouse_press(self, event, world_pos):
        if event.button() != Qt.LeftButton or world_pos is None:
            return
        snap = self.snap.snap_point(world_pos, self.scene, last_point=self.center)
        pt = snap.point

        if self.center is None:
            self.center = pt
        else:
            radius = np.linalg.norm(pt - self.center)
            if radius > 1e-6:
                self._create_polygon(self.center, radius)
            self.center = None
            self.preview = None
        self.vp.update()

    def on_mouse_move(self, event, world_pos):
        if self.center is None or world_pos is None:
            return
        snap = self.snap.snap_point(world_pos, self.scene, last_point=self.center)
        self.preview = snap.point
        self.vp.update()

    def on_key_press(self, event):
        if event.key() == Qt.Key_Escape:
            self.center = None
            self.preview = None
            self.vp.update()
        elif event.key() == Qt.Key_BracketLeft:
            self.sides = max(3, self.sides - 1)
            self.vp.update()
        elif event.key() == Qt.Key_BracketRight:
            self.sides = min(64, self.sides + 1)
            self.vp.update()

    def _create_polygon(self, center: np.ndarray, radius: float):
        mesh = Mesh(name=f"Polygon{self.sides}")
        verts = []
        for i in range(self.sides):
            a = 2 * math.pi * i / self.sides - math.pi / 2
            x = center[0] + radius * math.cos(a)
            z = center[2] + radius * math.sin(a)
            verts.append(mesh.add_vertex([x, center[1], z]))
        for i in range(self.sides):
            mesh.add_edge(verts[i], verts[(i + 1) % self.sides])
        mesh.add_face(verts)
        self.scene.add_mesh(mesh)

    def draw_preview(self):
        if self.center is None or self.preview is None:
            return
        radius = np.linalg.norm(self.preview - self.center)
        glDisable(GL_DEPTH_TEST)
        glLineWidth(2.0)
        glColor3f(0.3, 0.85, 1.0)
        glBegin(GL_LINE_LOOP)
        for i in range(self.sides):
            a = 2 * math.pi * i / self.sides - math.pi / 2
            x = self.center[0] + radius * math.cos(a)
            z = self.center[2] + radius * math.sin(a)
            glVertex3f(x, self.center[1], z)
        glEnd()
        glEnable(GL_DEPTH_TEST)

    def status_text(self) -> str:
        if self.center is None:
            return f"Многоугольник ({self.sides} сторон): кликните центр  ·  [ ] — изменить стороны"
        return f"Многоугольник ({self.sides}): укажите радиус  ·  Esc — отмена"


class ArcTool(Tool):
    name = "arc"
    label = "Дуга"

    def __init__(self, viewport):
        super().__init__(viewport)
        self.points: List[np.ndarray] = []  # start, end, then bulge point
        self.preview: Optional[np.ndarray] = None
        self.segments = 24

    def on_activate(self):
        self.points.clear()
        self.preview = None

    def on_mouse_press(self, event, world_pos):
        if event.button() != Qt.LeftButton or world_pos is None:
            return
        last = self.points[-1] if self.points else None
        snap = self.snap.snap_point(world_pos, self.scene, last_point=last)
        pt = snap.point
        self.points.append(pt)

        if len(self.points) == 3:
            self._create_arc(self.points[0], self.points[1], self.points[2])
            self.points.clear()
            self.preview = None
        self.vp.update()

    def on_mouse_move(self, event, world_pos):
        if world_pos is None:
            return
        last = self.points[-1] if self.points else None
        snap = self.snap.snap_point(world_pos, self.scene, last_point=last)
        self.preview = snap.point
        self.vp.update()

    def on_key_press(self, event):
        if event.key() == Qt.Key_Escape:
            self.points.clear()
            self.preview = None
            self.vp.update()

    def _create_arc(self, p0, p1, p2):
        """Простая дуга через 3 точки (на плоскости XZ)."""
        # упрощённо: интерполяция по углу вокруг середины хорды
        mid = (p0 + p1) * 0.5
        # используем p2 как точку на дуге для определения выпуклости
        mesh = Mesh(name="Arc")
        verts = []
        for i in range(self.segments + 1):
            t = i / self.segments
            # квадратичная Безье p0 -> p2 -> p1
            pt = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p2 + t ** 2 * p1
            verts.append(mesh.add_vertex(pt))
        for i in range(len(verts) - 1):
            mesh.add_edge(verts[i], verts[i + 1])
        self.scene.add_mesh(mesh)

    def draw_preview(self):
        pts = list(self.points)
        if self.preview is not None:
            pts = pts + [self.preview]

        if len(pts) < 1:
            return

        glDisable(GL_DEPTH_TEST)
        glLineWidth(2.0)
        glColor3f(0.3, 0.85, 1.0)

        if len(pts) == 2:
            glBegin(GL_LINES)
            glVertex3fv(pts[0].astype(np.float32))
            glVertex3fv(pts[1].astype(np.float32))
            glEnd()
        elif len(pts) >= 3:
            p0, p1, p2 = pts[0], pts[1], pts[2]
            glBegin(GL_LINE_STRIP)
            for i in range(self.segments + 1):
                t = i / self.segments
                pt = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p2 + t ** 2 * p1
                glVertex3fv(pt.astype(np.float32))
            glEnd()

        glPointSize(8.0)
        glBegin(GL_POINTS)
        glColor3f(1.0, 0.9, 0.2)
        for p in self.points:
            glVertex3fv(p.astype(np.float32))
        if self.preview is not None:
            glColor3f(0.4, 0.9, 1.0)
            glVertex3fv(self.preview.astype(np.float32))
        glEnd()
        glEnable(GL_DEPTH_TEST)

    def status_text(self) -> str:
        n = len(self.points)
        if n == 0:
            return "Дуга: кликните начальную точку"
        if n == 1:
            return "Дуга: кликните конечную точку"
        return "Дуга: кликните точку на дуге  ·  Esc — отмена"
