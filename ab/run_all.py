#!/usr/bin/env python3
"""Run the A/B protocol: 6 rounds, alternating A/B, 20s scroll each.

Usage: python3 run_all.py [rounds]   (default 6, must be even)
Sites: ab/site-a/index.html (route A), ab/site-b/index.html (route B)
"""
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 6
assert rounds % 2 == 0, "rounds must be even"

order = []
for i in range(rounds):
    label = "A" if i % 2 == 0 else "B"
    order.append((label, f"file://{HERE}/site-{label.lower()}/index.html"))

for i, (label, url) in enumerate(order, 1):
    out = str(HERE / f"ab-r{i}-{label}")
    print(f"=== round {i}/{rounds}: route {label} ===", flush=True)
    r = subprocess.run([sys.executable, str(HERE / "driver.py"), url, out],
                       capture_output=True, text=True, timeout=300)
    print(r.stdout[-1500:] if r.stdout else "")
    if r.returncode != 0:
        print(f"ROUND {i} FAILED:\n{r.stderr[-2000:]}", flush=True)
    time.sleep(3)
print("ALL ROUNDS DONE")
