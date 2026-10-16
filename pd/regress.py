#!/usr/bin/env python3
"""Regression checks for the web PresentDamage change.

1. Pixel comparison: same clicks on site-before/site-after, diff screenshots.
2. Memory: usedJSHeapSize before/after a click series, both versions.

Usage: python3 regress.py before after
"""
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from cdp import CDP, wait_boot


def run(label, port, clicks=6):
    url = f"file://{HERE}/site-{label}/index.html"
    cdp = CDP(port, url)
    cdp.start()
    try:
        cdp.call("Page.enable")
        cdp.call("Runtime.enable")
        wait_boot(cdp)
        time.sleep(4)
        mem0 = cdp.evaluate("performance.memory.usedJSHeapSize")
        shots = []
        for i in range(clicks):
            cdp.click(705, 428)
            time.sleep(0.8)
            p = HERE / f"reg-{label}-{i}.png"
            cdp.screenshot(str(p))
            shots.append(p)
        mem1 = cdp.evaluate("performance.memory.usedJSHeapSize")
        print(f"[{label}] heap before={mem0 / 1048576:.1f}MB "
              f"after={mem1 / 1048576:.1f}MB", flush=True)
        return shots
    finally:
        cdp.stop()


if __name__ == "__main__":
    from PIL import Image, ImageChops
    import numpy as np

    labels = sys.argv[1:]
    base = 23800 + random.randint(0, 999)
    all_shots = {}
    for l in labels:
        all_shots[l] = run(l, base)
        base += 10
        time.sleep(2)
    for i in range(len(all_shots[labels[0]])):
        a = Image.open(all_shots[labels[0]][i]).convert("RGB")
        b = Image.open(all_shots[labels[1]][i]).convert("RGB")
        diff = ImageChops.difference(a, b)
        if diff.getbbox():
            n = int((np.asarray(diff).sum(axis=2) > 0).sum())
            print(f"click {i}: DIFFER {n} px")
        else:
            print(f"click {i}: identical")
