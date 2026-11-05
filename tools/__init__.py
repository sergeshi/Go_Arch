"""Инструменты рисования и редактирования (в стиле SketchUp)."""

from .base import Tool
from .select_tool import SelectTool
from .draw_tools import LineTool, RectTool, CircleTool, PolygonTool, ArcTool
from .transform_tools import MoveTool, RotateTool, ScaleTool, ExtrudeTool

TOOL_CLASSES = {
    "select": SelectTool,
    "line": LineTool,
    "rect": RectTool,
    "circle": CircleTool,
    "polygon": PolygonTool,
    "arc": ArcTool,
    "move": MoveTool,
    "rotate": RotateTool,
    "scale": ScaleTool,
    "extrude": ExtrudeTool,
}

__all__ = [
    "Tool",
    "SelectTool",
    "LineTool",
    "RectTool",
    "CircleTool",
    "PolygonTool",
    "ArcTool",
    "MoveTool",
    "RotateTool",
    "ScaleTool",
    "ExtrudeTool",
    "TOOL_CLASSES",
]
