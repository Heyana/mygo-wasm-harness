#!/usr/bin/env python3
"""Shared Chrome/CDP bits for the wasm harnesses.

Chrome binary: $CHROME_BIN, else google-chrome / chromium / chromium-browser
on PATH, else /opt/meta-chromium/chrome.
Python dep: pip install websocket-client
"""
import json, os, shutil, subprocess, tempfile, time, urllib.request


def find_chrome():
    for cand in (os.environ.get("CHROME_BIN"),
                 shutil.which("google-chrome"),
                 shutil.which("chromium"),
                 shutil.which("chromium-browser"),
                 "/opt/meta-chromium/chrome"):
        if cand and os.path.exists(cand):
            return cand
    raise RuntimeError("no Chrome found: set CHROME_BIN")


class CDP:
    def __init__(self, port, url, extra_args=()):
        self.port = port
        self.url = url
        self.extra_args = list(extra_args)
        self.profile = tempfile.mkdtemp(prefix="chrome-harness-")
        self.proc = None
        self.ws = None
        self.seq = 0

    def start(self):
        import websocket
        cmd = [find_chrome(), "--headless=new",
               f"--remote-debugging-port={self.port}",
               "--remote-allow-origins=*",
               "--no-sandbox", "--disable-dev-shm-usage",
               "--allow-file-access-from-files",
               "--enable-precise-memory-info",
               "--window-size=1280,900",
               f"--user-data-dir={self.profile}"] + self.extra_args + [self.url]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(150):
                try:
                    targets = json.load(urllib.request.urlopen(
                        f"http://127.0.0.1:{self.port}/json/list", timeout=2))
                    pages = [t for t in targets if t["type"] == "page"
                             and t.get("url", "").startswith("file://")]
                    if pages:
                        self.ws = websocket.create_connection(
                            pages[0]["webSocketDebuggerUrl"], timeout=10)
                        return
                except Exception:
                    pass
                time.sleep(0.2)
            raise RuntimeError("devtools endpoint never came up")
        except Exception:
            self.stop()
            raise

    def call(self, method, params=None, timeout=30):
        self.seq += 1
        self.ws.send(json.dumps({"id": self.seq, "method": method, "params": params or {}}))
        end = time.time() + timeout
        while time.time() < end:
            d = json.loads(self.ws.recv())
            if d.get("id") == self.seq:
                if "error" in d:
                    raise RuntimeError(f"CDP {method}: {d['error']}")
                return d.get("result", {})
        raise RuntimeError(f"CDP {method}: timeout")

    def evaluate(self, expr, await_promise=False):
        r = self.call("Runtime.evaluate", {"expression": expr, "returnByValue": True,
                                           "awaitPromise": await_promise})
        if "exceptionDetails" in r:
            raise RuntimeError(f"JS error: {r['exceptionDetails']}")
        # call() returns d["result"]; the RemoteObject is at r["result"]
        inner = r.get("result", r)
        return inner["value"]

    def click(self, x, y):
        self.call("Input.dispatchMouseEvent",
                  {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1})
        self.call("Input.dispatchMouseEvent",
                  {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})

    def wheel(self, x=640, y=400, dy=120):
        self.call("Input.dispatchMouseEvent",
                  {"type": "mouseWheel", "x": x, "y": y, "deltaX": 0, "deltaY": dy})

    def screenshot(self, path):
        import base64
        r = self.call("Page.captureScreenshot", {"format": "png"})
        with open(path, "wb") as f:
            f.write(base64.b64decode(r["data"]))

    def stop(self):
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except Exception:
                self.proc.kill()
        shutil.rmtree(self.profile, ignore_errors=True)


def wait_boot(cdp, timeout=60):
    for _ in range(int(timeout / 0.5)):
        try:
            t = cdp.evaluate("document.title")
            n = cdp.evaluate("document.querySelectorAll('canvas').length")
        except Exception:
            time.sleep(0.5)
            continue
        if t.startswith("WASM ERROR"):
            raise RuntimeError(t)
        if n > 0:
            return
        time.sleep(0.5)
    raise RuntimeError("app never booted")
