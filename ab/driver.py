#!/usr/bin/env python3
"""A/B driver: loads a wasm site (file://) in headless Chromium, scrolls a
virtual list via CDP wheel events, and records rAF frame timestamps + heaps.

Usage: python3 driver.py <site_url> <out_prefix>
Writes <out_prefix>.json and prints the summary.
"""
import json
import os
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from cdp import CDP, wait_boot


def check_webgl(cdp):
    return cdp.evaluate("(()=>{const c=document.createElement('canvas');"
                        "const g=c.getContext('webgl2');"
                        "return g?g.getParameter(g.VERSION):null;})()")


def run_round(site_url, out_prefix, wheel_dy=160, measure_s=20, warmup_s=3):
    port = random.randint(20000, 40000)
    cdp = CDP(port, site_url, extra_args=("--enable-unsafe-swiftshader",))
    cdp.start()
    try:
        cdp.call("Page.enable")
        cdp.call("Runtime.enable")
        wait_boot(cdp)
        time.sleep(6)  # let first frames + fonts settle

        webgl = check_webgl(cdp)
        print(f"  webgl2: {webgl}")

        t0 = time.time()
        while time.time() - t0 < warmup_s:
            cdp.wheel(dy=wheel_dy)
            time.sleep(0.15)

        mem_start = cdp.evaluate("performance.memory.usedJSHeapSize")
        try:
            gomem_start = cdp.evaluate("window.__gomem()")
        except Exception:
            gomem_start = None
        cdp.evaluate("window.__frames=[]; window.__measuring=true;")
        t0 = time.time()
        ticks = 0
        while time.time() - t0 < measure_s:
            cdp.wheel(dy=wheel_dy)
            ticks += 1
            time.sleep(0.1)
        wall = time.time() - t0
        cdp.evaluate("window.__measuring=false;")
        frames = cdp.evaluate("window.__frames.slice()")
        mem_end = cdp.evaluate("performance.memory.usedJSHeapSize")
        try:
            gomem_end = cdp.evaluate("window.__gomem()")
        except Exception:
            gomem_end = None
        return {
            "webgl2": webgl,
            "wheel_ticks": ticks,
            "wall_s": wall,
            "frames": frames,
            "mem_start": mem_start,
            "mem_end": mem_end,
            "gomem_start": gomem_start,
            "gomem_end": gomem_end,
        }
    finally:
        cdp.stop()


def stats(frames, wall):
    n = len(frames)
    if n < 2:
        return {"n": n}
    iv = sorted(b - a for a, b in zip(frames, frames[1:]))

    def pct(p):
        return iv[min(len(iv) - 1, int(p * len(iv)))]

    slow = sum(1 for x in iv if x > 50.0)
    return {
        "n": n,
        "fps": n / wall,
        "p50_ms": pct(0.50),
        "p95_ms": pct(0.95),
        "p99_ms": pct(0.99),
        "max_ms": iv[-1],
        "slow_gt50ms": slow,
        "slow_ratio": slow / len(iv),
    }


if __name__ == "__main__":
    site_url, out_prefix = sys.argv[1], sys.argv[2]
    r = run_round(site_url, out_prefix)
    s = stats(r["frames"], r["wall_s"])
    out = {
        "webgl2": r["webgl2"],
        "wheel_ticks": r["wheel_ticks"],
        "wall_s": round(r["wall_s"], 2),
        "jsheap_start_mb": round(r["mem_start"] / 1048576, 2),
        "jsheap_end_mb": round(r["mem_end"] / 1048576, 2),
        "jsheap_delta_mb": round((r["mem_end"] - r["mem_start"]) / 1048576, 2),
        "goheap_start_mb": r["gomem_start"],
        "goheap_end_mb": r["gomem_end"],
        **{k: (round(v, 2) if isinstance(v, float) else v) for k, v in s.items()},
    }
    print(json.dumps(out, indent=1))
    with open(out_prefix + ".json", "w") as f:
        json.dump(out, f, indent=1)
