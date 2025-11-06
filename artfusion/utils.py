import os
import numpy as np
import cv2
from PySide6 import QtGui


def clamp01(x):
    import numpy as _np
    return _np.clip(x, 0.0, 1.0)


def ensure_bgr_u8(img):
    if img is None:
        return None
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img


def to_qimage(img_bgr):
    img_bgr = ensure_bgr_u8(img_bgr)
    h, w, _ = img_bgr.shape
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    qimg = QtGui.QImage(img_rgb.data, w, h, 3 * w, QtGui.QImage.Format.Format_RGB888)
    return qimg.copy()


def qpixmap_from_bgr(img_bgr):
    return QtGui.QPixmap.fromImage(to_qimage(img_bgr))


def load_image(path):
    # robust to unicode paths
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)


def save_image(path, img_bgr):
    ext = os.path.splitext(path)[1].lower() or ".png"
    params = []
    if ext in (".jpg", ".jpeg"):
        params = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
    ok, buf = cv2.imencode(ext, ensure_bgr_u8(img_bgr), params)
    if not ok:
        raise RuntimeError("imencode failed")
    with open(path, "wb") as f:
        f.write(buf.tobytes())