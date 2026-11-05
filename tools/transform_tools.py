"""Инструменты трансформации: Move, Rotate, Scale, Extrude."""

from __future__ import annotations

from typing import Optional, List
import math
import numpy as np
from OpenGL.GL import *
from PySide6.QtCore import Qt

from .base import Tool
from core.geometry import Mesh, Vertex, Face


class MoveTool(Tool):
    name = "move"
    label = "Перемещение"

    def __init__(self, viewport):
        super().__init__(viewport)
        self.start: Optional[np.ndarray] = None
        self.preview: Optional[np.ndarray] = None
        self.original_positions = {}  # id(vertex) -> pos

    def on_activate(self):
        self.start = None
        self.preview = None
        self.original_positions.clear()

    def on_mouse_press(self, event, world_pos):
        if event.button() != Qt.LeftButton or world_pos is None:
            return

        if not self.scene.selected:
            return

        snap = self.snap.snap_point(world_pos, self.scene)
        if self.start is None:
            self.start = snap.point
            self._store_originals()
        else:
            delta = snap.point - self.start
            # финальный snap дельты к сетке по осям
            delta = self._snap_delta(delta)
            self._apply_delta(delta)
            self.start = None
            self.preview = None
            self.original_positions.clear()
        self.vp.update()

    def on_mouse_move(self, event, world_pos):
        if self.start is None or world_pos is None:
            return
        snap = self.snap.snap_point(world_pos, self.scene, last_point=self.start)
        self.preview = snap.point
        delta = self._snap_delta(self.preview - self.start)
        self._apply_delta(delta)
        self.vp.update()

    def on_key_press(self, event):
        if event.key() == Qt.Key_Escape:
            self._restore_originals()
            self.start = None
            self.preview = None
            self.original_positions.clear()
            self.vp.update()

    def _snap_delta(self, delta: np.ndarray) -> np.ndarray:
        g = self.snap.grid_size
        if self.snap.grid_snap:
            delta = np.round(delta / g) * g
        # axis constraint if one component dominates
        if self.snap.axis_snap:
            abs_d = np.abs(delta)
            mx = abs_d.max()
            if mx > 1e-8:
                mask = abs_d < mx * 0.15
                delta = delta.copy()
                delta[mask] = 0.0
        return delta

    def _selected_vertices(self) -> List[Vertex]:
        verts = []
        for obj in self.scene.selected:
            if isinstance(obj, Mesh):
                verts.extend(obj.vertices)
            elif isinstance(obj, Vertex):
                verts.append(obj)
            elif isinstance(obj, Face):
                verts.extend(obj.vertices)
        # unique by id
        seen = set()
        result = []
        for v in verts:
            if id(v) not in seen:
                seen.add(id(v))
                result.append(v)
        return result

    def _store_originals(self):
        self.original_positions = {id(v): v.position.copy() for v in self._selected_vertices()}

    def _restore_originals(self):
        for v in self._selected_vertices():
            if id(v) in self.original_positions:
                v.position[:] = self.original_positions[id(v)]

    def _apply_delta(self, delta: np.ndarray):
        for v in self._selected_vertices():
            if id(v) in self.original_positions:
                v.position[:] = self.original_positions[id(v)] + delta

    def draw_preview(self):
        if self.start is None or self.preview is None:
            return
        glDisable(GL_DEPTH_TEST)
        glLineWidth(2.0)
        glColor3f(1.0, 0.8, 0.2)
        glBegin(GL_LINES)
        glVertex3fv(self.start.astype(np.float32))
        glVertex3fv(self.preview.astype(np.float32))
        glEnd()
        glEnable(GL_DEPTH_TEST)

    def status_text(self) -> str:
        if not self.scene.selected:
            return "Перемещение: сначала выделите объект"
        if self.start is None:
            return "Перемещение: кликните базовую точку"
        return "Перемещение: кликните целевую точку  ·  Esc — отмена"


class RotateTool(Tool):
    name = "rotate"
    label = "Поворот"

    def __init__(self, viewport):
        super().__init__(viewport)
        self.center: Optional[np.ndarray] = None
        self.start_angle = 0.0
        self.current_angle = 0.0
        self.original_positions = {}
        self.axis = np.array([0.0, 1.0, 0.0])  # Y-up

    def on_activate(self):
        self.center = None
        self.original_positions.clear()

    def on_mouse_press(self, event, world_pos):
        if event.button() != Qt.LeftButton or world_pos is None:
            return
        if not self.scene.selected:
            return

        if self.center is None:
            # центр = центр выделения или клик
            verts = self._selected_vertices()
            if verts:
                self.center = np.mean([v.position for v in verts], axis=0)
            else:
                self.center = world_pos.copy()
            self._store_originals()
            self.start_vec = world_pos - self.center
            self.start_vec[1] = 0  # project to XZ
        else:
            # фиксируем
            self.center = None
            self.original_positions.clear()
        self.vp.update()

    def on_mouse_move(self, event, world_pos):
        if self.center is None or world_pos is None:
            return
        vec = world_pos - self.center
        vec[1] = 0
        if np.linalg.norm(self.start_vec) < 1e-8 or np.linalg.norm(vec) < 1e-8:
            return
        a0 = math.atan2(self.start_vec[2], self.start_vec[0])
        a1 = math.atan2(vec[2], vec[0])
        angle = a1 - a0
        # snap angle to 15 degrees
        if self.snap.enabled:
            step = math.radians(15)
            angle = round(angle / step) * step
        self.current_angle = angle
        self._apply_rotation(angle)
        self.vp.update()

    def on_key_press(self, event):
        if event.key() == Qt.Key_Escape:
            self._restore_originals()
            self.center = None
            self.original_positions.clear()
            self.vp.update()

    def _selected_vertices(self):
        verts = []
        for obj in self.scene.selected:
            if isinstance(obj, Mesh):
                verts.extend(obj.vertices)
            elif isinstance(obj, Vertex):
                verts.append(obj)
            elif isinstance(obj, Face):
                verts.extend(obj.vertices)
        seen = set()
        result = []
        for v in verts:
            if id(v) not in seen:
                seen.add(id(v))
                result.append(v)
        return result

    def _store_originals(self):
        self.original_positions = {id(v): v.position.copy() for v in self._selected_vertices()}

    def _restore_originals(self):
        for v in self._selected_vertices():
            if id(v) in self.original_positions:
                v.position[:] = self.original_positions[id(v)]

    def _apply_rotation(self, angle: float):
        c, s = math.cos(angle), math.sin(angle)
        # rotate around Y
        for v in self._selected_vertices():
            if id(v) not in self.original_positions:
                continue
            p = self.original_positions[id(v)] - self.center
            x = p[0] * c - p[2] * s
            z = p[0] * s + p[2] * c
            v.position[:] = self.center + np.array([x, p[1], z])

    def status_text(self) -> str:
        if not self.scene.selected:
            return "Поворот: сначала выделите объект"
        if self.center is None:
            return "Поворот: кликните чтобы задать центр / начать"
        deg = math.degrees(self.current_angle)
        return f"Поворот: {deg:.1f}°  ·  клик — зафиксировать  ·  Esc — отмена"


class ScaleTool(Tool):
    name = "scale"
    label = "Масштаб"

    def __init__(self, viewport):
        super().__init__(viewport)
        self.center: Optional[np.ndarray] = None
        self.start_dist = 1.0
        self.original_positions = {}

    def on_activate(self):
        self.center = None
        self.original_positions.clear()

    def on_mouse_press(self, event, world_pos):
        if event.button() != Qt.LeftButton or world_pos is None:
            return
        if not self.scene.selected:
            return

        verts = self._selected_vertices()
        if not verts:
            return

        if self.center is None:
            self.center = np.mean([v.position for v in verts], axis=0)
            self._store_originals()
            self.start_dist = max(np.linalg.norm(world_pos - self.center), 0.01)
        else:
            self.center = None
            self.original_positions.clear()
        self.vp.update()

    def on_mouse_move(self, event, world_pos):
        if self.center is None or world_pos is None:
            return
        dist = max(np.linalg.norm(world_pos - self.center), 0.01)
        factor = dist / self.start_dist
        # snap factor
        if self.snap.enabled:
            factor = round(factor * 10) / 10  # 0.1 steps
        self._apply_scale(factor)
        self.vp.update()

    def on_key_press(self, event):
        if event.key() == Qt.Key_Escape:
            self._restore_originals()
            self.center = None
            self.original_positions.clear()
            self.vp.update()

    def _selected_vertices(self):
        verts = []
        for obj in self.scene.selected:
            if isinstance(obj, Mesh):
                verts.extend(obj.vertices)
            elif isinstance(obj, Vertex):
                verts.append(obj)
            elif isinstance(obj, Face):
                verts.extend(obj.vertices)
        seen = set()
        result = []
        for v in verts:
            if id(v) not in seen:
                seen.add(id(v))
                result.append(v)
        return result

    def _store_originals(self):
        self.original_positions = {id(v): v.position.copy() for v in self._selected_vertices()}

    def _restore_originals(self):
        for v in self._selected_vertices():
            if id(v) in self.original_positions:
                v.position[:] = self.original_positions[id(v)]

    def _apply_scale(self, factor: float):
        for v in self._selected_vertices():
            if id(v) not in self.original_positions:
                continue
            p = self.original_positions[id(v)] - self.center
            v.position[:] = self.center + p * factor

    def status_text(self) -> str:
        if not self.scene.selected:
            return "Масштаб: сначала выделите объект"
        if self.center is None:
            return "Масштаб: кликните чтобы начать"
        return "Масштаб: двигайте мышь  ·  клик — зафиксировать  ·  Esc — отмена"


class ExtrudeTool(Tool):
    name = "extrude"
    label = "Выдавливание"

    def __init__(self, viewport):
        super().__init__(viewport)
        self.face: Optional[Face] = None
        self.start_y = 0.0
        self.height = 0.0
        self.preview_mesh: Optional[Mesh] = None
        self.base_verts: List[np.ndarray] = []

    def on_activate(self):
        self.face = None
        self.preview_mesh = None
        self.base_verts = []

    def on_mouse_press(self, event, world_pos):
        if event.button() != Qt.LeftButton:
            return

        if self.face is None:
            # ищем выделенную грань или грань меша
            face = None
            for obj in self.scene.selected:
                if isinstance(obj, Face):
                    face = obj
                    break
                if isinstance(obj, Mesh) and obj.faces:
                    face = obj.faces[0]  # для демо — первая грань
                    break
            if face is None:
                # fallback: первая грань первого меша
                meshes = self.scene.all_meshes()
                if meshes and meshes[0].faces:
                    face = meshes[0].faces[0]
            if face is None:
                return

            self.face = face
            self.base_verts = [v.position.copy() for v in face.vertices]
            self.start_y = world_pos[1] if world_pos is not None else 0.0
            self.height = 0.0
        else:
            # фиксируем выдавливание
            if abs(self.height) > 1e-6:
                self._commit_extrude()
            self.face = None
            self.preview_mesh = None
            self.base_verts = []
        self.vp.update()

    def on_mouse_move(self, event, world_pos):
        if self.face is None or world_pos is None:
            return
        h = world_pos[1] - self.start_y
        # snap height
        g = self.snap.grid_size
        if self.snap.grid_snap:
            h = round(h / g) * g
        self.height = h
        self.vp.update()

    def on_key_press(self, event):
        if event.key() == Qt.Key_Escape:
            self.face = None
            self.preview_mesh = None
            self.base_verts = []
            self.vp.update()

    def _commit_extrude(self):
        if not self.base_verts:
            return
        mesh = Mesh(name="Extrude")
        n = len(self.base_verts)
        bottom = [mesh.add_vertex(p) for p in self.base_verts]
        top = [mesh.add_vertex(p + np.array([0, self.height, 0])) for p in self.base_verts]

        # рёбра и грани
        for i in range(n):
            mesh.add_edge(bottom[i], bottom[(i + 1) % n])
            mesh.add_edge(top[i], top[(i + 1) % n])
            mesh.add_edge(bottom[i], top[i])

        mesh.add_face(bottom)
        mesh.add_face(list(reversed(top)))
        for i in range(n):
            mesh.add_face([bottom[i], bottom[(i + 1) % n], top[(i + 1) % n], top[i]])

        self.scene.add_mesh(mesh)

    def draw_preview(self):
        if self.face is None or not self.base_verts:
            return
        n = len(self.base_verts)
        top = [p + np.array([0.0, self.height, 0.0]) for p in self.base_verts]

        glDisable(GL_DEPTH_TEST)
        glLineWidth(2.0)
        glColor3f(0.3, 0.9, 0.5)

        # верх
        glBegin(GL_LINE_LOOP)
        for p in top:
            glVertex3fv(p.astype(np.float32))
        glEnd()

        # стойки
        glBegin(GL_LINES)
        for i in range(n):
            glVertex3fv(self.base_verts[i].astype(np.float32))
            glVertex3fv(top[i].astype(np.float32))
        glEnd()

        glEnable(GL_DEPTH_TEST)

    def status_text(self) -> str:
        if self.face is None:
            return "Выдавливание: выделите грань/объект и кликните"
        h = self.units.format(abs(self.height))
        return f"Выдавливание: высота {h}  ·  клик — зафиксировать  ·  Esc — отмена"
