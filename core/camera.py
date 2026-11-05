"""Orbit camera in SketchUp style."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from OpenGL.GL import (
    glLoadIdentity,
    glMatrixMode,
    glMultMatrixf,
    GL_MODELVIEW,
    GL_PROJECTION,
)
from OpenGL.GLU import gluPerspective, gluLookAt


@dataclass
class Camera:
    """
    Камера с орбитой вокруг целевой точки (как в SketchUp).

    - target  : точка, вокруг которой вращаемся
    - distance: расстояние от target до камеры
    - yaw, pitch: углы в градусах
    """

    target: np.ndarray = None
    distance: float = 12.0
    yaw: float = 45.0      # горизонтальный угол
    pitch: float = 30.0    # вертикальный угол
    fov: float = 45.0
    near: float = 0.1
    far: float = 1000.0

    def __post_init__(self):
        if self.target is None:
            self.target = np.array([0.0, 0.0, 0.0], dtype=np.float64)

    # ------------------------------------------------------------------
    # Математика
    # ------------------------------------------------------------------
    def position(self) -> np.ndarray:
        """Мировые координаты камеры."""
        yaw_rad = math.radians(self.yaw)
        pitch_rad = math.radians(self.pitch)

        x = self.distance * math.cos(pitch_rad) * math.sin(yaw_rad)
        y = self.distance * math.sin(pitch_rad)
        z = self.distance * math.cos(pitch_rad) * math.cos(yaw_rad)

        return self.target + np.array([x, y, z], dtype=np.float64)

    def view_matrix(self) -> np.ndarray:
        """4x4 матрица вида (column-major для OpenGL)."""
        eye = self.position()
        up = np.array([0.0, 1.0, 0.0], dtype=np.float64)

        # look-at
        f = self.target - eye
        f = f / np.linalg.norm(f)
        s = np.cross(f, up)
        s = s / np.linalg.norm(s)
        u = np.cross(s, f)

        m = np.eye(4, dtype=np.float64)
        m[0, 0:3] = s
        m[1, 0:3] = u
        m[2, 0:3] = -f
        m[0:3, 3] = -m[0:3, 0:3] @ eye
        return m.T  # OpenGL expects column-major when using glMultMatrixf with flattened

    # ------------------------------------------------------------------
    # Управление
    # ------------------------------------------------------------------
    def orbit(self, dx: float, dy: float, sensitivity: float = 0.4):
        """Вращение вокруг target (средняя кнопка)."""
        self.yaw += dx * sensitivity
        self.pitch -= dy * sensitivity
        # ограничиваем pitch, чтобы не переворачивалось
        self.pitch = max(-89.0, min(89.0, self.pitch))

    def pan(self, dx: float, dy: float, sensitivity: float = 0.01):
        """Панорамирование (Shift + средняя)."""
        eye = self.position()
        forward = self.target - eye
        forward = forward / (np.linalg.norm(forward) + 1e-8)
        right = np.cross(forward, np.array([0.0, 1.0, 0.0]))
        right = right / (np.linalg.norm(right) + 1e-8)
        up = np.cross(right, forward)

        # скорость пана зависит от расстояния
        scale = self.distance * sensitivity
        self.target += (-right * dx + up * dy) * scale

    def zoom(self, delta: float, sensitivity: float = 0.15):
        """Приближение / отдаление (колёсико)."""
        factor = 1.0 - delta * sensitivity
        self.distance = max(0.5, min(500.0, self.distance * factor))

    def look_at(self, point: np.ndarray):
        self.target = np.asarray(point, dtype=np.float64)

    # ------------------------------------------------------------------
    # Применение в OpenGL (legacy matrix mode для простоты старта)
    # ------------------------------------------------------------------
    def apply(self, aspect: float):
        """Устанавливает projection + modelview."""
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.fov, aspect, self.near, self.far)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        eye = self.position()
        gluLookAt(
            eye[0], eye[1], eye[2],
            self.target[0], self.target[1], self.target[2],
            0.0, 1.0, 0.0,
        )
