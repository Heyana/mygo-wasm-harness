#!/usr/bin/env python3
"""Summarize an A/B run: bundle + fps + memory, routes A vs B.

Reads ab/bundle.json (written by build.sh) and ab/ab-rN-{A,B}.json
(written by run_all.py), prints the three-number comparison table.

Usage: python3 report.py
"""
import glob
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_rounds(label):
    out = []
    for p in sorted(glob.glob(str(HERE / f"ab-r*-{label}.json"))):
        out.append(json.loads(Path(p).read_text()))
    return out


def summarize(label):
    rounds = load_rounds(label)
    if not rounds:
        return None
    fps = [r["fps"] for r in rounds if r.get("fps")]
    p95 = [r["p95_ms"] for r in rounds if r.get("p95_ms")]
    slow = [r["slow_ratio"] for r in rounds if r.get("slow_ratio") is not None]
    jsd = [r["jsheap_delta_mb"] for r in rounds if r.get("jsheap_delta_mb") is not None]
    goe = [r["goheap_end_mb"] for r in rounds if r.get("goheap_end_mb") is not None]
    med = lambda xs: round(statistics.median(xs), 2) if xs else None
    return {
        "rounds": len(rounds),
        "fps_med": med(fps),
        "p95_ms_med": med(p95),
        "slow_ratio_med": med(slow),
        "jsheap_delta_mb_med": med(jsd),
        "goheap_end_mb_med": med(goe),
    }


def main():
    bundle = json.loads((HERE / "bundle.json").read_text())
    a, b = summarize("A"), summarize("B")
    if not a or not b:
        print("no round data: run run_all.py first")
        return
    print(f"rounds: A x{a['rounds']}, B x{b['rounds']}")
    print()
    print("BUNDLE")
    for label in ("a", "b"):
        r = bundle[label]
        print(f"  {label.upper()}: {r['raw'] / 1048576:.2f} MB raw / "
              f"{r['gzip9'] / 1048576:.2f} MB gzip-9")
    print(f"  diff: {(bundle['a']['raw'] - bundle['b']['raw']) / bundle['b']['raw'] * 100:+.1f}% raw, "
          f"{(bundle['a']['gzip9'] - bundle['b']['gzip9']) / bundle['b']['gzip9'] * 100:+.1f}% gzip "
          f"(+ means A bigger)")
    print()
    print("FPS (scroll workload, 20s rounds)")
    for label, s in (("A", a), ("B", b)):
        print(f"  {label}: {s['fps_med']} fps med, p95 {s['p95_ms_med']} ms, "
              f"slow-frame ratio {s['slow_ratio_med']}")
    print()
    print("MEMORY")
    for label, s in (("A", a), ("B", b)):
        print(f"  {label}: jsheap delta {s['jsheap_delta_mb_med']} MB, "
              f"goheap end {s['goheap_end_mb_med']} MB")
    print()
    print("NOTE: headless Chromium here has no real GPU. A WebGL2 route that")
    print("looks slow here may be 60fps on real hardware - do not judge the")
    print("route by VM fps alone. Bundle and memory numbers are solid.")


if __name__ == "__main__":
    main()
