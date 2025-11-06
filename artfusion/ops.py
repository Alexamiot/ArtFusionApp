import numpy as np
import cv2
from .utils import clamp01


class Ops:
    @staticmethod
    def adjust(img, brightness=0, contrast=1.0, saturation=1.0, hue=0, gamma=1.0):
        x = img.astype(np.float32) / 255.0
        x = x * contrast + (brightness / 255.0)
        x = clamp01(x)
        hsv = cv2.cvtColor((x * 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[..., 1] *= saturation
        hsv[..., 0] = (hsv[..., 0] + (hue / 2)) % 180
        hsv[..., 1] = np.clip(hsv[..., 1], 0, 255)
        hsv[..., 2] = np.clip(hsv[..., 2], 0, 255)
        x = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32) / 255.0
        x = np.power(np.maximum(x, 1e-8), 1.0 / max(gamma, 1e-6))
        return (x * 255).astype(np.uint8)

    @staticmethod
    def grayscale(img):
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)

    @staticmethod
    def sepia(img, strength=0.8):
        m = np.array([[0.272, 0.534, 0.131],
                      [0.349, 0.686, 0.168],
                      [0.393, 0.769, 0.189]], dtype=np.float32)
        y = (img.astype(np.float32) @ m.T)
        y = np.clip(y, 0, 255).astype(np.uint8)
        return cv2.addWeighted(img, 1.0 - strength, y, strength, 0)

    @staticmethod
    def blur(img, k=7):
        k = max(1, int(k) | 1)
        return cv2.GaussianBlur(img, (k, k), 0)

    @staticmethod
    def sharpen(img, amount=1.0):
        blurred = cv2.GaussianBlur(img, (0, 0), 2.0)
        return cv2.addWeighted(img, 1 + amount, blurred, -amount, 0)

    @staticmethod
    def edges(img, thresh1=100, thresh2=200):
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        e = cv2.Canny(g, thresh1, thresh2)
        return cv2.cvtColor(e, cv2.COLOR_GRAY2BGR)

    @staticmethod
    def cartoon(img, bilateral=9, edges_thresh=150):
        color = cv2.bilateralFilter(img, d=9, sigmaColor=bilateral, sigmaSpace=bilateral)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        e = cv2.Canny(gray, edges_thresh / 2, edges_thresh)
        e = cv2.bitwise_not(e)
        e = cv2.cvtColor(e, cv2.COLOR_GRAY2BGR)
        return cv2.bitwise_and(color, e)

    @staticmethod
    def vignette(img, strength=0.6):
        h, w = img.shape[:2]
        y, x = np.ogrid[:h, :w]
        cy, cx = h / 2, w / 2
        r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        max_r = np.sqrt(cx ** 2 + cy ** 2)
        mask = 1 - strength * (r / max_r)
        mask = np.clip(mask, 0, 1)
        mask = np.dstack([mask] * 3)
        out = img.astype(np.float32) * mask
        return np.clip(out, 0, 255).astype(np.uint8)

    @staticmethod
    def glow(img, amount=0.6, blur_ks=21):
        blur_ks = max(1, int(blur_ks) | 1)
        blur = cv2.GaussianBlur(img, (blur_ks, blur_ks), 0)
        return cv2.addWeighted(img, 1.0, blur, amount, 0)

    @staticmethod
    def blend(a, b, mode='normal', alpha=0.5):
        if b is None:
            return a
        h, w = a.shape[:2]
        b = cv2.resize(b, (w, h), interpolation=cv2.INTER_LINEAR)
        ar = a.astype(np.float32) / 255.0
        br = b.astype(np.float32) / 255.0
        if mode == 'normal':
            cr = ar * (1 - alpha) + br * alpha
        elif mode == 'multiply':
            cr = ar * br
        elif mode == 'screen':
            cr = 1 - (1 - ar) * (1 - br)
        elif mode == 'overlay':
            mask = ar <= 0.5
            cr = np.empty_like(ar)
            cr[mask] = 2 * ar[mask] * br[mask]
            cr[~mask] = 1 - 2 * (1 - ar[~mask]) * (1 - br[~mask])
        elif mode == 'darken':
            cr = np.minimum(ar, br)
        elif mode == 'lighten':
            cr = np.maximum(ar, br)
        elif mode == 'add':
            cr = np.clip(ar + br * alpha, 0, 1)
        else:
            cr = ar * (1 - alpha) + br * alpha
        return (cr * 255).astype(np.uint8)

    # --- New: Otsu mask + composite ---
    @staticmethod
    def otsu_mask(img, invert=False, feather=0):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, m = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if invert:
            m = 255 - m
        if feather > 0:
            k = max(1, int(feather) | 1)
            m = cv2.GaussianBlur(m, (k, k), 0)
        return m  # uint8 0..255

    @staticmethod
    def composite_by_mask(base, other, mask_u8):
        h, w = base.shape[:2]
        other = cv2.resize(other, (w, h), interpolation=cv2.INTER_LINEAR)
        a = (mask_u8.astype(np.float32) / 255.0)[..., None]  # 0..1
        out = base.astype(np.float32) * (1 - a) + other.astype(np.float32) * a
        return np.clip(out, 0, 255).astype(np.uint8)

    @staticmethod
    def reinhard_color_transfer(source, target):
        src = cv2.cvtColor(source, cv2.COLOR_BGR2LAB).astype(np.float32)
        tgt = cv2.cvtColor(target, cv2.COLOR_BGR2LAB).astype(np.float32)

        def stats(x):
            l, a, b = cv2.split(x)
            return (l.mean(), a.mean(), b.mean()), (l.std() + 1e-6, a.std() + 1e-6, b.std() + 1e-6)

        (smean, sstd) = stats(src)
        (tmean, tstd) = stats(tgt)
        l, a, b = cv2.split(src)
        l = (l - smean[0]) * (tstd[0] / sstd[0]) + tmean[0]
        a = (a - smean[1]) * (tstd[1] / sstd[1]) + tmean[1]
        b = (b - smean[2]) * (tstd[2] / sstd[2]) + tmean[2]
        o = cv2.merge([l, a, b])
        o = np.clip(o, 0, 255).astype(np.uint8)
        return cv2.cvtColor(o, cv2.COLOR_LAB2BGR)