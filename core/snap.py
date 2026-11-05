"""Система привязок (snap)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from .geometry import Mesh, Vertex, Edge, Face
from .scene import Scene


@dataclass
class SnapResult:
    point: np.ndarray
    kind: str  # "grid" | "vertex" | "edge" | "midpoint" | "axis" | "none"
    source: object = None


class SnapSystem:
    def __init__(self):
        self.enabled = True
        self.grid_snap = True
        self.vertex_snap = True
        self.edge_snap = True
        self.midpoint_snap = True
        self.axis_snap = True  # привязка к осям X/Y/Z от последней точки

        self.grid_size = 0.1  # в метрах (10 см по умолчанию)
        self.snap_pixel_threshold = 12  # пикселей

    def set_grid_size(self, size_meters: float):
        self.grid_size = max(0.001, size_meters)

    def snap_point(
        self,
        world_point: np.ndarray,
        scene: Scene,
        last_point: Optional[np.ndarray] = None,
        screen_pos: Optional[Tuple[int, int]] = None,
        camera=None,
        viewport_size: Optional[Tuple[int, int]] = None,
    ) -> SnapResult:
        """
        Привязывает точку. Приоритет:
        1. Вершины
        2. Середины рёбер
        3. Рёбра (проекция)
        4. Оси от last_point
        5. Сетка
        """
        if not self.enabled:
            return SnapResult(world_point.copy(), "none")

        best: Optional[SnapResult] = None
        best_dist = float("inf")

        # --- вершины ---
        if self.vertex_snap:
            for mesh in scene.all_meshes():
                for v in mesh.vertices:
                    d = np.linalg.norm(v.position - world_point)
                    if d < best_dist and d < self.grid_size * 2.5:
                        best_dist = d
                        best = SnapResult(v.position.copy(), "vertex", v)

        # --- середины рёбер ---
        if self.midpoint_snap:
            for mesh in scene.all_meshes():
                for e in mesh.edges:
                    mid = (e.v1.position + e.v2.position) * 0.5
                    d = np.linalg.norm(mid - world_point)
                    if d < best_dist and d < self.grid_size * 2.0:
                        best_dist = d
                        best = SnapResult(mid, "midpoint", e)

        # --- оси от last_point ---
        if self.axis_snap and last_point is not None:
            delta = world_point - last_point
            abs_d = np.abs(delta)
            # если движение почти по одной оси
            thresh = self.grid_size * 1.5
            snapped = world_point.copy()
            kind = "axis"
            if abs_d[0] > abs_d[1] and abs_d[0] > abs_d[2]:
                # доминирует X
                if abs_d[1] < thresh and abs_d[2] < thresh:
                    snapped[1] = last_point[1]
                    snapped[2] = last_point[2]
                    d = np.linalg.norm(snapped - world_point)
                    if d < best_dist:
                        best_dist = d
                        best = SnapResult(snapped, "axis")
            elif abs_d[1] > abs_d[0] and abs_d[1] > abs_d[2]:
                if abs_d[0] < thresh and abs_d[2] < thresh:
                    snapped[0] = last_point[0]
                    snapped[2] = last_point[2]
                    d = np.linalg.norm(snapped - world_point)
                    if d < best_dist:
                        best_dist = d
                        best = SnapResult(snapped, "axis")
            else:
                if abs_d[0] < thresh and abs_d[1] < thresh:
                    snapped[0] = last_point[0]
                    snapped[1] = last_point[1]
                    d = np.linalg.norm(snapped - world_point)
                    if d < best_dist:
                        best_dist = d
                        best = SnapResult(snapped, "axis")

        # --- сетка ---
        if self.grid_snap:
            g = self.grid_size
            grid_pt = np.round(world_point / g) * g
            d = np.linalg.norm(grid_pt - world_point)
            if d < best_dist and d < g * 0.6:
                best = SnapResult(grid_pt, "grid")

        if best is not None:
            return best
        return SnapResult(world_point.copy(), "none")
