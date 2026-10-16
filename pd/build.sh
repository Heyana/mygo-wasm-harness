#!/usr/bin/env bash
# Build the two counter-native sites for the PresentDamage test.
# Uses throwaway git worktrees so your checkout is never touched.
# Usage: build.sh <before_repo> <before_ref> <after_repo> <after_ref>
# Example: build.sh ~/mygo-upstream main ~/mygo-upstream web-present-damage
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BEFORE_REPO="$1"; BEFORE_REF="$2"; AFTER_REPO="$3"; AFTER_REF="$4"

build_one() { # repo ref label
  local repo="$1" ref="$2" label="$3"
  local dir="$HERE/site-$label" wt
  wt="$(mktemp -d)"
  rm -rf "$dir"; mkdir -p "$dir"
  cp "$HERE/site-template/index.html" "$dir/index.html"
  git -C "$repo" worktree add -f --detach "$wt" "$ref" >/dev/null 2>&1
  ( cd "$wt" && GOOS=js GOARCH=wasm CGO_ENABLED=0 go build \
      -trimpath "-ldflags=-s -w -X github.com/egoist/mygo.production=1" \
      -o "$dir/app.wasm" ./examples/counter-native )
  cp "$(go env GOROOT)/lib/wasm/wasm_exec.js" "$dir/wasm_exec.js"
  git -C "$repo" worktree remove --force "$wt"
  echo "built site-$label from $(basename "$repo") @ $ref: $(stat -c%s "$dir/app.wasm") bytes"
}

build_one "$BEFORE_REPO" "$BEFORE_REF" before
build_one "$AFTER_REPO" "$AFTER_REF" after
echo "run: python3 $HERE/measure.py before after"
