import http.server
import socketserver
import os
import sys
from functools import partial

_server = None

def get_web_root() -> str:
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    extensions_map = http.server.SimpleHTTPRequestHandler.extensions_map.copy()
    extensions_map.update({
        ".html": "text/html; charset=utf-8",
        ".js":   "application/javascript; charset=utf-8",
        ".css":  "text/css; charset=utf-8",
    })

    def log_message(self, format, *args):
        return

class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

def run_widgets(port: int):
    global _server
    try:
        web_root = get_web_root()
        handler = partial(QuietHandler, directory=web_root)
        with ThreadingHTTPServer(("", int(port)), handler) as httpd:
            _server = httpd
            print(f"Hosting widgets on localhost:{port} (dir={web_root})")
            httpd.serve_forever(poll_interval=0.5)
    except Exception as e:
        print("Widgets host error:", repr(e))

def close_widgets():
    global _server
    try:
        if _server:
            _server.shutdown()
            _server.server_close()
            _server = None
    except Exception:
        pass
