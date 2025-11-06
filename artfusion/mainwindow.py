# -*- coding: utf-8 -*-
import os
from PySide6 import QtGui
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QFileDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QComboBox,
    QFrame, QSplitter, QTabWidget, QMessageBox, QStyleFactory, QSizePolicy,
    QGroupBox, QPushButton, QButtonGroup
)

from .utils import load_image, save_image
from .imageview import ImageView
from .ops import Ops


class ArtFusion(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArtFusion Studio")
        self.resize(1480, 840)
        self._apply_dark_theme()

        # Two images and per-image bases
        self.images = [None, None]
        self.bases = [None, None]
        self.undo_stack = [[], []]
        self.redo_stack = [[], []]
        self.active = 0  # 0 or 1

        # Viewers
        self.viewer1 = ImageView()
        self.viewer2 = ImageView()

        # Left toolbar
        left = QWidget(); left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)

        # Load/save per-image
        row = QHBoxLayout()
        btn_open1 = QPushButton("Ouvrir 1…"); btn_open2 = QPushButton("Ouvrir 2…")
        btn_save = QPushButton("Exporter actif…")
        for b in (btn_open1, btn_open2, btn_save):
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_open1.clicked.connect(lambda: self.open_image(slot=0))
        btn_open2.clicked.connect(lambda: self.open_image(slot=1))
        btn_save.clicked.connect(self.save_active)
        row.addWidget(btn_open1); row.addWidget(btn_open2)
        left_layout.addLayout(row); left_layout.addWidget(btn_save)

        # Undo/Redo row
        ur = QHBoxLayout()
        btn_undo = QPushButton("Annuler")
        btn_redo = QPushButton("Rétablir")
        for b in (btn_undo, btn_redo):
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_undo.clicked.connect(self.undo)
        btn_redo.clicked.connect(self.redo)
        ur.addWidget(btn_undo); ur.addWidget(btn_redo)
        left_layout.addLayout(ur)

        left_layout.addWidget(self._separator())

        # Active toggle
        toggle_row = QHBoxLayout()
        self.btn_img1 = QPushButton("Image 1"); self.btn_img2 = QPushButton("Image 2")
        for b in (self.btn_img1, self.btn_img2):
            b.setCheckable(True)
            b.setStyleSheet("QPushButton:checked{background:#4068ff;color:white;font-weight:600}")
        bg = QButtonGroup(self); bg.setExclusive(True)
        bg.addButton(self.btn_img1, 0); bg.addButton(self.btn_img2, 1)
        self.btn_img1.setChecked(True)
        self.btn_img1.clicked.connect(lambda: self.set_active(0))
        self.btn_img2.clicked.connect(lambda: self.set_active(1))
        toggle_row.addWidget(self.btn_img1); toggle_row.addWidget(self.btn_img2)
        left_layout.addLayout(toggle_row)
        left_layout.addWidget(self._separator())

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._panel_adjust(), "Réglages")
        tabs.addTab(self._panel_filters(), "Filtres")
        tabs.addTab(self._panel_fx(), "Effets")
        tabs.addTab(self._panel_blend(), "Fusion")
        tabs.addTab(self._panel_color_match(), "Filtre d'image")
        tabs.addTab(self._panel_otsu(), "Otsu")
        left_layout.addWidget(tabs, 1)
        left_layout.addStretch(1)

        # Center: side by side viewers
        right = QWidget(); rlayout = QHBoxLayout(right); rlayout.setContentsMargins(0,0,0,0)
        split_views = QSplitter(); split_views.addWidget(self.viewer1); split_views.addWidget(self.viewer2)
        split_views.setStretchFactor(0, 1); split_views.setStretchFactor(1, 1)
        rlayout.addWidget(split_views)

        split_main = QSplitter(); split_main.addWidget(left); split_main.addWidget(right)
        split_main.setStretchFactor(1, 1)
        self.setCentralWidget(split_main)

        self.setAcceptDrops(True)

    # --- Panels ---
    def _panel_adjust(self):
        w = QWidget(); v = QVBoxLayout(w)
        self.s_brightness = self._labeled_slider(v, "Luminosité", -100, 100, 0)
        self.s_contrast = self._labeled_slider(v, "Contraste", 10, 300, 100)
        self.s_saturation = self._labeled_slider(v, "Saturation", 0, 300, 100)
        self.s_hue = self._labeled_slider(v, "Teinte", -180, 180, 0)
        self.s_gamma = self._labeled_slider(v, "Gamma", 50, 250, 100)
        for s in [self.s_brightness, self.s_contrast, self.s_saturation, self.s_hue, self.s_gamma]:
            s.valueChanged.connect(self._apply_adjust_live)
        btn_apply = QPushButton("Appliquer sur actif"); btn_apply.clicked.connect(self.apply_adjust)
        v.addWidget(btn_apply); v.addStretch(1); return w

    def _panel_filters(self):
        w = QWidget(); v = QVBoxLayout(w)
        h = QHBoxLayout(); self.cmb_filter = QComboBox(); self.cmb_filter.addItems(["Gris", "Sepia", "Flou", "Netteté", "Contours", "Cartoon"])
        h.addWidget(QLabel("Filtre")); h.addWidget(self.cmb_filter, 1); v.addLayout(h)
        self.s_filter_strength = self._labeled_slider(v, "Intensité", 0, 300, 100)
        btn = QPushButton("Appliquer sur actif"); btn.clicked.connect(self.apply_filter)
        v.addWidget(btn); v.addStretch(1); return w

    def _panel_fx(self):
        w = QWidget(); v = QVBoxLayout(w)
        self.s_vignette = self._labeled_slider(v, "Vignette", 0, 100, 60)
        self.s_glow = self._labeled_slider(v, "Lueur", 0, 200, 60)
        btn = QPushButton("Appliquer sur actif"); btn.clicked.connect(self.apply_fx)
        v.addWidget(btn); v.addStretch(1); return w

    def _panel_blend(self):
        w = QWidget(); v = QVBoxLayout(w)
        from PySide6.QtWidgets import QLabel as _QLabel
        from PySide6.QtWidgets import QComboBox as _QComboBox
        hb = QHBoxLayout(); self.cmb_blend = _QComboBox(); self.cmb_blend.addItems(["normal", "multiply", "screen", "overlay", "darken", "lighten", "add"])
        hb.addWidget(_QLabel("Mode")); hb.addWidget(self.cmb_blend, 1); v.addLayout(hb)
        self.s_alpha = self._labeled_slider(v, "Opacité", 0, 100, 50)
        btn_apply = QPushButton("Fusionner actif avec autre"); btn_apply.clicked.connect(self.apply_blend)
        v.addWidget(btn_apply); v.addStretch(1); return w

    def _panel_color_match(self):
        w = QWidget(); v = QVBoxLayout(w)
        info = QLabel("Transférer l'ambiance de l'autre image vers l'image active."); info.setWordWrap(True)
        v.addWidget(info)
        btn_apply = QPushButton("Transfert Reinhard (autre → actif)"); btn_apply.clicked.connect(self.apply_color_transfer)
        v.addWidget(btn_apply); v.addStretch(1); return w

    def _panel_otsu(self):
        w = QWidget(); v = QVBoxLayout(w)
        info = QLabel("Seuil d'Otsu sur l'image active. Les pixels seuil=1 sont remplacés par l'autre image.")
        info.setWordWrap(True); v.addWidget(info)
        self.chk_invert = QPushButton("Inverser le masque"); self.chk_invert.setCheckable(True)
        self.s_feather = self._labeled_slider(v, "Adoucissement (px)", 0, 51, 7)
        btn = QPushButton("Otsu → Composite (actif remplacé par autre)"); btn.clicked.connect(self.apply_otsu_composite)
        v.addWidget(self.chk_invert); v.addWidget(btn); v.addStretch(1); return w

    # --- Helpers UI ---
    def _separator(self):
        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setFrameShadow(QFrame.Sunken); return line

    def _labeled_slider(self, layout, name, minv, maxv, val):
        box = QGroupBox(name); v = QVBoxLayout(box)
        s = QSlider(Qt.Horizontal); s.setRange(minv, maxv); s.setValue(val)
        lbl = QLabel(str(val)); s.valueChanged.connect(lambda vv: lbl.setText(str(vv)))
        v.addWidget(s); v.addWidget(lbl); layout.addWidget(box); return s

    def set_active(self, idx):
        self.active = idx

    # --- Image I/O ---
    def open_image(self, slot):
        path, _ = QFileDialog.getOpenFileName(self, f"Ouvrir {slot+1}", "", "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if not path:
            return
        img = load_image(path)
        if img is None:
            QMessageBox.critical(self, "Erreur", "Impossible de charger l'image.")
            return
        self.images[slot] = img.copy(); self.bases[slot] = img.copy()
        self.undo_stack[slot].clear(); self.redo_stack[slot].clear()
        self._refresh_views()

    def save_active(self):
        img = self.images[self.active]
        if img is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter", f"image{self.active+1}.png", "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if not path:
            return
        try:
            save_image(path, img)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de l'export: {e}")

    # --- Undo/Redo on active ---
    def push_state(self):
        img = self.images[self.active]
        if img is not None:
            self.undo_stack[self.active].append(img.copy())
            self.redo_stack[self.active].clear()

    def undo(self):
        st = self.undo_stack[self.active]
        if not st:
            return
        cur = self.images[self.active]
        self.redo_stack[self.active].append(cur.copy())
        self.images[self.active] = st.pop()
        self.bases[self.active] = self.images[self.active].copy()
        self._refresh_views()

    def redo(self):
        st = self.redo_stack[self.active]
        if not st:
            return
        cur = self.images[self.active]
        self.undo_stack[self.active].append(cur.copy())
        self.images[self.active] = st.pop()
        self.bases[self.active] = self.images[self.active].copy()
        self._refresh_views()

    # --- Adjustments ---
    def _apply_adjust_live(self):
        base = self.bases[self.active]
        if base is None:
            return
        img = Ops.adjust(
            base,
            brightness=self.s_brightness.value(),
            contrast=self.s_contrast.value() / 100.0,
            saturation=self.s_saturation.value() / 100.0,
            hue=self.s_hue.value(),
            gamma=self.s_gamma.value() / 100.0,
        )
        self._set_view_temp(img)

    def apply_adjust(self):
        base = self.bases[self.active]
        if base is None:
            return
        self.push_state()
        img = Ops.adjust(
            base,
            brightness=self.s_brightness.value(),
            contrast=self.s_contrast.value() / 100.0,
            saturation=self.s_saturation.value() / 100.0,
            hue=self.s_hue.value(),
            gamma=self.s_gamma.value() / 100.0,
        )
        self.images[self.active] = img
        self.bases[self.active] = img.copy()
        self._refresh_views()

    # --- Filters ---
    def apply_filter(self):
        img = self.images[self.active]
        if img is None:
            return
        name = self.cmb_filter.currentText(); strength = self.s_filter_strength.value() / 100.0
        self.push_state()
        if name == "Gris":
            img = Ops.grayscale(img)
        elif name == "Sepia":
            img = Ops.sepia(img, strength)
        elif name == "Flou":
            k = int(1 + strength * 30); img = Ops.blur(img, k)
        elif name == "Netteté":
            img = Ops.sharpen(img, amount=0.5 + strength)
        elif name == "Contours":
            t = int(50 + strength * 200); img = Ops.edges(img, t // 2, t)
        elif name == "Cartoon":
            img = Ops.cartoon(img, bilateral=int(5 + strength * 30), edges_thresh=int(80 + strength * 200))
        self.images[self.active] = img; self.bases[self.active] = img.copy(); self._refresh_views()

    # --- FX ---
    def apply_fx(self):
        img = self.images[self.active]
        if img is None:
            return
        self.push_state(); out = img.copy()
        if self.s_vignette.value() > 0:
            out = Ops.vignette(out, strength=self.s_vignette.value() / 100.0)
        if self.s_glow.value() > 0:
            out = Ops.glow(out, amount=self.s_glow.value() / 100.0)
        self.images[self.active] = out; self.bases[self.active] = out.copy(); self._refresh_views()

    # --- Blend active with other ---
    def apply_blend(self):
        a = self.images[self.active]
        b = self.images[1 - self.active]
        if a is None or b is None:
            QMessageBox.information(self, "Info", "Chargez les deux images.")
            return
        self.push_state()
        mode = self.cmb_blend.currentText(); alpha = self.s_alpha.value() / 100.0
        out = Ops.blend(a, b, mode=mode, alpha=alpha)
        self.images[self.active] = out; self.bases[self.active] = out.copy(); self._refresh_views()

    # --- Color transfer other → active ---
    def apply_color_transfer(self):
        a = self.images[self.active]
        b = self.images[1 - self.active]
        if a is None or b is None:
            QMessageBox.information(self, "Info", "Chargez les deux images.")
            return
        self.push_state()
        out = Ops.reinhard_color_transfer(a, b)
        self.images[self.active] = out; self.bases[self.active] = out.copy(); self._refresh_views()

    # --- Otsu composite ---
    def apply_otsu_composite(self):
        a = self.images[self.active]
        b = self.images[1 - self.active]
        if a is None or b is None:
            QMessageBox.information(self, "Info", "Chargez les deux images.")
            return
        self.push_state()
        invert = self.chk_invert.isChecked(); feather = self.s_feather.value()
        mask = Ops.otsu_mask(a, invert=invert, feather=feather)
        out = Ops.composite_by_mask(a, b, mask)
        self.images[self.active] = out; self.bases[self.active] = out.copy(); self._refresh_views()

    # --- View refresh ---
    def _refresh_views(self):
        if self.images[0] is not None:
            self.viewer1.set_image(self.images[0])
        else:
            self.viewer1.set_image(None)
        if self.images[1] is not None:
            self.viewer2.set_image(self.images[1])
        else:
            self.viewer2.set_image(None)
        QTimer.singleShot(0, self.viewer1.fit_in_view)
        QTimer.singleShot(0, self.viewer2.fit_in_view)

    def _set_view_temp(self, img):
        # live preview only on active viewer
        if self.active == 0:
            self.viewer1.set_image(img)
        else:
            self.viewer2.set_image(img)

    # --- Theme ---
    def _apply_dark_theme(self):
        from PySide6.QtWidgets import QApplication
        QApplication.setStyle(QStyleFactory.create("Fusion"))
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(30, 30, 30))
        palette.setColor(QtGui.QPalette.WindowText, Qt.white)
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(18, 18, 18))
        palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(45, 45, 45))
        palette.setColor(QtGui.QPalette.ToolTipBase, Qt.white)
        palette.setColor(QtGui.QPalette.ToolTipText, Qt.white)
        palette.setColor(QtGui.QPalette.Text, Qt.white)
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor(45, 45, 45))
        palette.setColor(QtGui.QPalette.ButtonText, Qt.white)
        palette.setColor(QtGui.QPalette.BrightText, Qt.red)
        palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(64, 128, 255))
        palette.setColor(QtGui.QPalette.HighlightedText, Qt.black)
        from PySide6.QtWidgets import QApplication as _QApp
        _QApp.setPalette(palette)
