#!/usr/bin/env bash
# Build the A/B bench sites from two mygo checkouts.
# The SAME workload source (ab/benchlist-src) is built against each repo via
# a replace directive, so only the module (and thus the backend) differs.
# Uses throwaway git worktrees so your checkouts are never touched.
#
# Usage: build.sh <repo_a> <ref_a> <repo_b> <ref_b>
# Example: build.sh ~/mygo web-wasm ~/mygo-upstream v0.5.5
#   route A = your Canvas2D fork, route B = upstream WebGL2
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

build_one() { # repo ref label
  local repo="$1" ref="$2" label="$3"
  local dir="$HERE/site-$label" wt builddir
  wt="$(mktemp -d)"; builddir="$(mktemp -d)"
  rm -rf "$dir"; mkdir -p "$dir"
  cp "$HERE/site-template/index.html" "$dir/index.html"
  git -C "$repo" worktree add -f --detach "$wt" "$ref" >/dev/null 2>&1
  cp "$HERE/benchlist-src/"*.go "$builddir/"
  ( cd "$builddir" && go mod init benchlist >/dev/null 2>&1
    go mod edit -require=github.com/egoist/mygo@v0.0.0 \
      -replace=github.com/egoist/mygo="$wt"
    GOOS=js GOARCH=wasm CGO_ENABLED=0 go mod tidy >/dev/null 2>&1 || true
    GOOS=js GOARCH=wasm CGO_ENABLED=0 go build \
      -trimpath "-ldflags=-s -w -X github.com/egoist/mygo.production=1" \
      -o "$dir/app.wasm" . )
  cp "$(go env GOROOT)/lib/wasm/wasm_exec.js" "$dir/wasm_exec.js"
  git -C "$repo" worktree remove --force "$wt"
  rm -rf "$builddir"
  echo "built site-$label from $(basename "$repo") @ $ref: $(stat -c%s "$dir/app.wasm") bytes"
}

build_one "$1" "$2" a
build_one "$3" "$4" b
python3 - "$HERE" << 'EOF'
import gzip, json, sys
from pathlib import Path
h = Path(sys.argv[1])
rec = {}
for label in ("a", "b"):
    p = h / f"site-{label}" / "app.wasm"
    raw = p.stat().st_size
    with open(p, "rb") as f:
        gz = len(gzip.compress(f.read(), 9))
    rec[label] = {"raw": raw, "gzip9": gz}
(h / "bundle.json").write_text(json.dumps(rec, indent=1))
print(f"bundle A: {rec['a']['raw']} raw / {rec['a']['gzip9']} gzip-9")
print(f"bundle B: {rec['b']['raw']} raw / {rec['b']['gzip9']} gzip-9")
EOF
echo "run: python3 $HERE/run_all.py  &&  python3 $HERE/report.py"
