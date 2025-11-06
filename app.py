#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from PySide6.QtWidgets import QApplication
from artfusion.mainwindow import ArtFusion


def main():
    app = QApplication(sys.argv)
    win = ArtFusion()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()