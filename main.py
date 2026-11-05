#!/usr/bin/env python3
"""Go_Arch — точка входа."""

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QSurfaceFormat

from ui.main_window import MainWindow


def main():
    # Настройки OpenGL
    fmt = QSurfaceFormat()
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    fmt.setVersion(2, 1)          # совместимый профиль для простоты
    fmt.setProfile(QSurfaceFormat.CompatibilityProfile)
    fmt.setSamples(4)             # MSAA
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(sys.argv)
    app.setApplicationName("Go_Arch")
    app.setOrganizationName("Go_Arch")
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
