"""Система единиц измерения."""

from __future__ import annotations

from enum import Enum


class Unit(Enum):
    MM = "mm"
    CM = "cm"
    M = "m"


# Внутренние единицы сцены — метры.
# Все координаты в Scene хранятся в метрах.

_SCALE_TO_METERS = {
    Unit.MM: 0.001,
    Unit.CM: 0.01,
    Unit.M: 1.0,
}

_SCALE_FROM_METERS = {
    Unit.MM: 1000.0,
    Unit.CM: 100.0,
    Unit.M: 1.0,
}


class UnitSystem:
    def __init__(self, unit: Unit = Unit.CM):
        self.unit = unit

    def to_internal(self, value: float) -> float:
        """Из текущих единиц пользователя → метры."""
        return value * _SCALE_TO_METERS[self.unit]

    def from_internal(self, value: float) -> float:
        """Из метров → текущие единицы пользователя."""
        return value * _SCALE_FROM_METERS[self.unit]

    def format(self, value_internal: float, precision: int = 2) -> str:
        v = self.from_internal(value_internal)
        return f"{v:.{precision}f} {self.unit.value}"

    def set_unit(self, unit: Unit):
        self.unit = unit
