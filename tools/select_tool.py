"""Инструмент выбора."""

from __future__ import annotations

from typing import Optional
import numpy as np
from PySide6.QtCore import Qt

from .base import Tool
from core.geometry import Mesh, Vertex, Edge, Face


class SelectTool(Tool):
    name = "select"
    label = "Выбор"

    def on_mouse_press(self, event, world_pos: Optional[np.ndarray]):
        if event.button() != Qt.LeftButton:
            return

        additive = bool(event.modifiers() & Qt.ControlModifier)

        hit = self._pick(world_pos)
        if hit is not None:
            self.scene.select(hit, additive=additive)
            self.vp.status_message.emit(f"Выбрано: {type(hit).__name__}")
        elif not additive:
            self.scene.clear_selection()
            self.vp.status_message.emit("Выделение снято")

        self.vp.selection_changed.emit()
        self.vp.update()

    def _pick(self, world_pos: Optional[np.ndarray]):
        if world_pos is None:
            return None

        best = None
        best_dist = 0.6  # метры — порог для вершин/рёбер на земле

        for mesh in self.scene.all_meshes():
            # вершины — расстояние в 3D, но смягчаем по Y
            for v in mesh.vertices:
                d = self._xz_dist(world_pos, v.position)
                if d < best_dist:
                    best_dist = d
                    best = v

            for e in mesh.edges:
                d = self._dist_point_segment_xz(world_pos, e.v1.position, e.v2.position)
                if d < best_dist:
                    best_dist = d
                    best = e

        # если близко к мешу целиком — выбираем меш
        for mesh in self.scene.all_meshes():
            c = mesh.center()
            d = self._xz_dist(world_pos, c)
            mn, mx = mesh.bounding_box()
            # клик внутри AABB в проекции XZ
            if (mn[0] - 0.3 <= world_pos[0] <= mx[0] + 0.3 and
                    mn[2] - 0.3 <= world_pos[2] <= mx[2] + 0.3):
                if best is None or d < best_dist + 0.5:
                    best = mesh
                    best_dist = d

        return best

    @staticmethod
    def _xz_dist(a, b) -> float:
        dx = a[0] - b[0]
        dz = a[2] - b[2]
        return float(np.sqrt(dx * dx + dz * dz))

    @staticmethod
    def _dist_point_segment_xz(p, a, b) -> float:
        ab = np.array([b[0] - a[0], b[2] - a[2]], dtype=np.float64)
        ap = np.array([p[0] - a[0], p[2] - a[2]], dtype=np.float64)
        denom = float(np.dot(ab, ab)) + 1e-12
        t = float(np.dot(ap, ab)) / denom
        t = max(0.0, min(1.0, t))
        proj = np.array([a[0], a[2]]) + t * ab
        d = proj - np.array([p[0], p[2]])
        return float(np.linalg.norm(d))

    def status_text(self) -> str:
        n = len(self.scene.selected)
        if n:
            return f"Выбор: выделено {n}  ·  Ctrl+клик — добавить"
        return "Выбор: кликните по объекту / ребру / вершине"
