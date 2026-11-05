"""Базовый класс инструмента."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, List
import numpy as np

if TYPE_CHECKING:
    from ui.viewport import Viewport3D


class Tool:
    name = "base"
    label = "Tool"

    def __init__(self, viewport: "Viewport3D"):
        self.vp = viewport
        self.active = False

    @property
    def scene(self):
        return self.vp.scene

    @property
    def camera(self):
        return self.vp.camera

    @property
    def snap(self):
        return self.vp.snap

    @property
    def units(self):
        return self.vp.units

    def activate(self):
        self.active = True
        self.on_activate()

    def deactivate(self):
        self.active = False
        self.on_deactivate()

    def on_activate(self):
        pass

    def on_deactivate(self):
        pass

    def on_mouse_press(self, event, world_pos: Optional[np.ndarray]):
        pass

    def on_mouse_move(self, event, world_pos: Optional[np.ndarray]):
        pass

    def on_mouse_release(self, event, world_pos: Optional[np.ndarray]):
        pass

    def on_key_press(self, event):
        pass

    def draw_preview(self):
        """Рисуется внутри paintGL после сцены."""
        pass

    def status_text(self) -> str:
        return self.label
