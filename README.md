# mygo-wasm-harness

MyGo WASM 路线的两套实测工具。都是 headless Chromium + `file://` 跑（这台 VM 上 Chrome 会拦截 `127.0.0.1` 的本地服务，`file://` 是绕法）。

## 前置

- Go（能编 wasm 就行）
- Chrome / Chromium：`CHROME_BIN` 环境变量，或 PATH 里有 `google-chrome` / `chromium`
- `pip install websocket-client`（pd 的 regress 还要 `pillow numpy`）

## 两套工具测什么

| 目录 | 测什么 | workload |
|---|---|---|
| `pd/` | **上传量**：无 WebGL2 降级路径每帧传多少字节（PR #434 的效果） | `examples/counter-native`，点 `+` 按钮（小 damage） |
| `ab/` | **A/B**：包体、帧率、内存，Canvas2D 路线 vs 上游 WebGL2 路线 | `benchlist-src`（500 行虚拟列表，持续滚轮 20s） |

## 分支对照表（别搞混）

| 测试 | site | 源码 | 分支 | 说明 |
|---|---|---|---|---|
| pd | `site-before` | mygo-upstream | `main` | #434 之前：整帧上传 |
| pd | `site-after` | mygo-upstream | `web-present-damage` | #434：只传 damage |
| ab | `site-a` | Heyana/mygo | `origin/web-wasm` | 我们的 Canvas2D 路线 |
| ab | `site-b` | egoist/mygo | `v0.5.5` | 上游 WebGL2 路线 |

注意：pd 用的都是 **mygo-upstream**（干净的上游跟踪仓库），ab 的 A 用的是 **Heyana/mygo fork**。两套测试互相独立。

## 明天怎么测（复制粘贴版）

```bash
git clone https://github.com/Heyana/mygo-wasm-harness.git
cd mygo-wasm-harness
pip install websocket-client

# --- pd：验证 #434（约 2 分钟）---
./pd/build.sh ~/mygo-upstream main ~/mygo-upstream web-present-damage
python3 pd/measure.py before after
# 看 bytes/click：before ~5.4MB，after ~0.28MB（约 19x）

# pd 回归：像素 + 内存（约 3 分钟）
pip install pillow numpy
python3 pd/regress.py before after
# 6 张截图应全部 identical；两版 heap 应无差别

# --- ab：路线 A/B 对比（约 8 分钟，6 轮 x 20s+）---
./ab/build.sh ~/mygo web-wasm ~/mygo-upstream v0.5.5
python3 ab/run_all.py
python3 ab/report.py
# 一键出三组数字：包体（raw/gzip）+ 帧率（fps/p95/慢帧率）+ 内存（js堆/go堆）
# 每轮原始 JSON 存 ab-rN-{A,B}.json，可复核
```

构建脚本都用 git worktree，不会动你的工作树。`site-*` 目录是构建产物，已 gitignore。

## 结果解读（2026-10-17 实测，供对照）

- **pd**：before 5,461,333 B/click → after 283,634 B/click（19.3x）；截图像素全同；堆内存无差别（省的是 CPU 和带宽，不是堆）
- **ab 包体**：A 10.97MB / B 11.38MB（只差 3.6%，包体不再是选型论据）
- **ab 帧率**：VM 无 GPU，SwiftShader 下 B 只有 0.93fps（软件光栅病理，不可推真机）；A 稳 60fps（兼容性论据的量化版）
- **ab 内存**：两边无差别

caveat：VM 无真实 GPU，WebGL2 的真机帧率必须真机测，这套工具只能证"不崩 + 包体 + 内存"。

## 文件

- `cdp.py`：Chrome/CDP 公共封装（两套测试共用）
- `pd/measure.py`：上传量主测试；`pd/regress.py`：像素回归+内存
- `ab/driver.py`：单轮；`ab/run_all.py`：6 轮 A/B 交替
- `ab/benchlist-src/`：A/B 共用的 workload 源码（两边同一份，只换 module）
