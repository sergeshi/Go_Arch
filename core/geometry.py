"""Базовые геометрические примитивы сцены."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple
import uuid

import numpy as np


def _id() -> str:
    return str(uuid.uuid4())[:8]


@dataclass
class Vertex:
    position: np.ndarray  # shape (3,)
    id: str = field(default_factory=_id)
    selected: bool = False

    def __post_init__(self):
        self.position = np.asarray(self.position, dtype=np.float64)


@dataclass
class Edge:
    v1: Vertex
    v2: Vertex
    id: str = field(default_factory=_id)
    selected: bool = False

    @property
    def points(self) -> Tuple[np.ndarray, np.ndarray]:
        return self.v1.position, self.v2.position


@dataclass
class Face:
    """Простая грань (полигон). Вершины должны идти в порядке обхода."""
    vertices: List[Vertex]
    id: str = field(default_factory=_id)
    selected: bool = False
    normal: Optional[np.ndarray] = None

    def __post_init__(self):
        if self.normal is None and len(self.vertices) >= 3:
            self.recompute_normal()

    def recompute_normal(self):
        if len(self.vertices) < 3:
            self.normal = np.array([0.0, 1.0, 0.0])
            return
        a = self.vertices[0].position
        b = self.vertices[1].position
        c = self.vertices[2].position
        n = np.cross(b - a, c - a)
        norm = np.linalg.norm(n)
        self.normal = n / norm if norm > 1e-8 else np.array([0.0, 1.0, 0.0])


@dataclass
class Group:
    """Группа объектов (как в SketchUp)."""
    name: str = "Group"
    children: List = field(default_factory=list)  # Mesh | Group
    transform: np.ndarray = field(default_factory=lambda: np.eye(4, dtype=np.float64))
    id: str = field(default_factory=_id)
    selected: bool = False


@dataclass
class Mesh:
    """Простая полигональная сетка."""
    vertices: List[Vertex] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    faces: List[Face] = field(default_factory=list)
    name: str = "Mesh"
    id: str = field(default_factory=_id)
    selected: bool = False

    def add_vertex(self, pos) -> Vertex:
        v = Vertex(np.asarray(pos, dtype=np.float64))
        self.vertices.append(v)
        return v

    def add_edge(self, v1: Vertex, v2: Vertex) -> Edge:
        e = Edge(v1, v2)
        self.edges.append(e)
        return e

    def add_face(self, verts: List[Vertex]) -> Face:
        f = Face(verts)
        self.faces.append(f)
        return f

    def clear_selection(self):
        for v in self.vertices:
            v.selected = False
        for e in self.edges:
            e.selected = False
        for f in self.faces:
            f.selected = False
        self.selected = False

    def bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        if not self.vertices:
            return np.zeros(3), np.zeros(3)
        pts = np.array([v.position for v in self.vertices])
        return pts.min(axis=0), pts.max(axis=0)

    def center(self) -> np.ndarray:
        mn, mx = self.bounding_box()
        return (mn + mx) * 0.5
