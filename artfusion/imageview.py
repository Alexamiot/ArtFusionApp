from PySide6 import QtGui
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from .utils import qpixmap_from_bgr


class ImageView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.pix = QGraphicsPixmapItem()
        self.scene().addItem(self.pix)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(24, 24, 24)))
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

    def set_image(self, img_bgr):
        if img_bgr is None:
            self.pix.setPixmap(QtGui.QPixmap())
            return
        pm = qpixmap_from_bgr(img_bgr)
        self.pix.setPixmap(pm)
        self.scene().setSceneRect(pm.rect())

    def fit_in_view(self):
        rect = self.scene().itemsBoundingRect()
        if rect.isNull():
            return
        self.fitInView(rect, Qt.KeepAspectRatio)