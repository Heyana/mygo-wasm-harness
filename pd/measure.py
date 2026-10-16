#!/usr/bin/env python3
"""PresentDamage vs PresentPixels in the no-WebGL2 fallback.

Builds two sites with pd/build.sh (before/after), then for each:
forces the no-WebGL2 fallback, instruments putImageData (calls + bytes),
clicks the counter button 15x (small damage), and reports bytes/click.

Usage: python3 measure.py before after   # labels = pd/site-<label>/
"""
import os
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from cdp import CDP, wait_boot


def measure(label, port, clicks=15, click_xy=(705, 428)):
    url = f"file://{HERE}/site-{label}/index.html"
    cdp = CDP(port, url)
    cdp.start()
    try:
        cdp.call("Page.enable")
        cdp.call("Runtime.enable")
        wait_boot(cdp)
        time.sleep(4)
        webgl = cdp.evaluate("(()=>{const c=document.createElement('canvas');"
                             "return c.getContext('webgl2');})()")
        print(f"[{label}] webgl2 forced null: {webgl is None}", flush=True)
        cdp.evaluate("window.__putStats={calls:0,bytes:0,newImage:0}; "
                     "window.__frames=[]; window.__measuring=true;")
        for _ in range(clicks):
            cdp.click(*click_xy)
            time.sleep(0.6)
        cdp.evaluate("window.__measuring=false;")
        stats = cdp.evaluate("window.__putStats")
        frames = cdp.evaluate("window.__frames.slice()")
        if len(frames) >= 2:
            dts = sorted(b - a for a, b in zip(frames, frames[1:]))
            p50 = dts[len(dts) // 2]
        else:
            p50 = None
        print(f"[{label}] clicks={clicks} putCalls={stats['calls']} "
              f"putBytes={stats['bytes']} newImage={stats.get('newImage', 0)} "
              f"bytes/click={stats['bytes'] // max(clicks, 1)} "
              f"rAFframes={len(frames)} p50frame_ms={p50}", flush=True)
    finally:
        cdp.stop()


if __name__ == "__main__":
    base = 23500 + random.randint(0, 999)
    for label in sys.argv[1:]:
        measure(label, base)
        base += 10
        time.sleep(2)
