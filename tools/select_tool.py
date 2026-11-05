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

        # Простой выбор: ближайший меш к точке на плоскости Y=0 или к существующей геометрии
        hit = self._pick(world_pos)
        if hit is not None:
            self.scene.select(hit, additive=additive)
        elif not additive:
            self.scene.clear_selection()

        self.vp.selection_changed.emit()
        self.vp.update()

    def _pick(self, world_pos: Optional[np.ndarray]):
        if world_pos is None:
            return None

        best = None
        best_dist = 0.35  # порог в метрах

        for mesh in self.scene.all_meshes():
            # вершины
            for v in mesh.vertices:
                d = np.linalg.norm(v.position - world_pos)
                if d < best_dist:
                    best_dist = d
                    best = v
            # рёбра (расстояние до отрезка)
            for e in mesh.edges:
                d = self._dist_point_segment(world_pos, e.v1.position, e.v2.position)
                if d < best_dist:
                    best_dist = d
                    best = e
            # если ничего точечного — весь меш
            if best is None:
                c = mesh.center()
                d = np.linalg.norm(c - world_pos)
                if d < 1.5:
                    best = mesh
                    best_dist = d

        return best

    @staticmethod
    def _dist_point_segment(p, a, b):
        ab = b - a
        t = np.dot(p - a, ab) / (np.dot(ab, ab) + 1e-12)
        t = max(0.0, min(1.0, t))
        proj = a + t * ab
        return np.linalg.norm(p - proj)
