#!/usr/bin/env python3
"""k-means color extraction.

  python extract_colors.py img1.jpg img2.png [--k 10]

Prints chromatic accent clusters (saturated, not-too-dark pixels) and the dominant
neutrals, each with HSV, so palette roles can be filled from real image pixels.
Near-white backdrops are ignored. Needs: pillow numpy scikit-learn.
"""
import argparse, colorsys
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans


def clusters(pixels, k):
    km = KMeans(n_clusters=min(k, len(pixels)), n_init=8, random_state=0).fit(pixels)
    counts = np.bincount(km.labels_, minlength=km.n_clusters)
    out = []
    for center, n in zip(km.cluster_centers_, counts):
        h, s, v = colorsys.rgb_to_hsv(*(center / 255))
        hexc = '#%02x%02x%02x' % tuple(int(round(x)) for x in center)
        out.append((hexc, n / len(pixels), round(h * 360), round(s, 2), round(v, 2)))
    return sorted(out, key=lambda t: -t[1])


def show(rows):
    for hexc, share, h, s, v in rows:
        print(f'    {hexc}  share={share:.3f}  H={h:3d}  S={s:.2f}  V={v:.2f}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('images', nargs='+')
    ap.add_argument('--k', type=int, default=10)
    args = ap.parse_args()
    for path in args.images:
        px = np.array(Image.open(path).convert('RGB')).reshape(-1, 3).astype(float)
        px = px[~(px > 235).all(axis=1)]                      # drop white backdrop
        hsv = np.array([colorsys.rgb_to_hsv(*(p / 255)) for p in px])
        print(f'== {path}')
        accents = px[(hsv[:, 1] > 0.30) & (hsv[:, 2] > 0.30)]
        neutrals = px[hsv[:, 1] <= 0.30]
        print('  accents:');  show(clusters(accents, args.k)) if len(accents) > 20 else None
        print('  neutrals:'); show(clusters(neutrals, 5)) if len(neutrals) > 20 else None


if __name__ == '__main__':
    main()
