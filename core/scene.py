"""Сцена — контейнер всей геометрии."""

from __future__ import annotations

from typing import List, Optional, Union

import numpy as np

from .geometry import Mesh, Group, Vertex, Edge, Face


class Scene:
    def __init__(self):
        self.root: List[Union[Mesh, Group]] = []
        self.selected: List[Union[Mesh, Group, Vertex, Edge, Face]] = []

    # ------------------------------------------------------------------
    # Добавление
    # ------------------------------------------------------------------
    def add_mesh(self, mesh: Mesh):
        self.root.append(mesh)
        return mesh

    def add_group(self, group: Group):
        self.root.append(group)
        return group

    def clear(self):
        self.root.clear()
        self.selected.clear()

    # ------------------------------------------------------------------
    # Выделение
    # ------------------------------------------------------------------
    def clear_selection(self):
        for obj in self.root:
            if isinstance(obj, Mesh):
                obj.clear_selection()
            elif isinstance(obj, Group):
                obj.selected = False
        self.selected.clear()

    def select(self, obj, additive: bool = False):
        if not additive:
            self.clear_selection()
        if obj not in self.selected:
            self.selected.append(obj)
        if hasattr(obj, "selected"):
            obj.selected = True

    # ------------------------------------------------------------------
    # Вспомогательные
    # ------------------------------------------------------------------
    def all_meshes(self) -> List[Mesh]:
        result = []

        def walk(items):
            for item in items:
                if isinstance(item, Mesh):
                    result.append(item)
                elif isinstance(item, Group):
                    walk(item.children)

        walk(self.root)
        return result

    def create_test_box(self, size: float = 2.0, center=(0, 1, 0)) -> Mesh:
        """Создаёт тестовый куб для отладки."""
        cx, cy, cz = center
        s = size / 2

        mesh = Mesh(name="TestBox")
        # 8 вершин
        positions = [
            (cx - s, cy - s, cz - s),
            (cx + s, cy - s, cz - s),
            (cx + s, cy + s, cz - s),
            (cx - s, cy + s, cz - s),
            (cx - s, cy - s, cz + s),
            (cx + s, cy - s, cz + s),
            (cx + s, cy + s, cz + s),
            (cx - s, cy + s, cz + s),
        ]
        verts = [mesh.add_vertex(p) for p in positions]

        # рёбра
        edge_idx = [
            (0, 1), (1, 2), (2, 3), (3, 0),  # низ
            (4, 5), (5, 6), (6, 7), (7, 4),  # верх
            (0, 4), (1, 5), (2, 6), (3, 7),  # стойки
        ]
        for i, j in edge_idx:
            mesh.add_edge(verts[i], verts[j])

        # грани (по часовой / против — не важно пока)
        faces_idx = [
            [0, 1, 2, 3],  # низ
            [4, 5, 6, 7],  # верх
            [0, 1, 5, 4],  # перед
            [1, 2, 6, 5],  # право
            [2, 3, 7, 6],  # зад
            [3, 0, 4, 7],  # лево
        ]
        for idxs in faces_idx:
            mesh.add_face([verts[i] for i in idxs])

        self.add_mesh(mesh)
        return mesh
