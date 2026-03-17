#!/usr/bin/env python3
"""HTTP server for Spike Ensemble.

Serves the web UI and provides API endpoints to start/stop the simulation.

Usage:
    python server.py              # Default port 8080
    python server.py --port 9000  # Custom port
"""

import argparse
import atexit
import json
import os
import signal
import subprocess
import sys
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

# ── Subprocess management ──

_process = None
_process_lock = threading.Lock()
_process_params = {}


def _load_env():
    """Load .env file into a dict."""
    env = os.environ.copy()
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    env[key.strip()] = value.strip()
    return env


def start_simulation(params):
    global _process, _process_params
    with _process_lock:
        if _process and _process.poll() is None:
            return False, 'Simulation already running'

        cmd = [
            sys.executable, 'run.py',
            '--bpm', str(params.get('bpm', 120)),
            '--duration', str(params.get('duration', 600)),
            '--threshold', str(params.get('threshold', 3)),
        ]

        env = _load_env()
        env['CL_SDK_WEBSOCKET'] = '1'

        _process = subprocess.Popen(
            cmd,
            cwd=os.path.dirname(__file__) or '.',
            env=env,
            start_new_session=True,  # own process group so we can kill the whole tree
        )
        _process_params = params
        return True, f'Started (PID {_process.pid})'


def _kill_process_group(proc):
    """Kill a process and all its children via process group."""
    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        proc.wait()


def stop_simulation():
    global _process
    with _process_lock:
        if not _process or _process.poll() is not None:
            _process = None
            return False, 'No simulation running'

        _kill_process_group(_process)
        _process = None
        return True, 'Stopped'


def get_status():
    with _process_lock:
        if _process and _process.poll() is None:
            return {'running': True, 'pid': _process.pid, 'params': _process_params}
        return {'running': False, 'pid': None, 'params': {}}


def _cleanup():
    if _process and _process.poll() is None:
        _kill_process_group(_process)

atexit.register(_cleanup)


# ── HTTP Handler ──

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, web_dir=None, **kwargs):
        self._web_dir = web_dir
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/':
            self.send_response(302)
            self.send_header('Location', '/standalone.html')
            self.end_headers()
        elif self.path == '/api/status':
            self._json_response(get_status())
        elif self.path == '/favicon.ico':
            self.send_error(204)
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/start':
            body = self._read_body()
            params = json.loads(body) if body else {}
            ok, msg = start_simulation(params)
            self._json_response({'ok': ok, 'message': msg}, 200 if ok else 409)
        elif self.path == '/api/stop':
            ok, msg = stop_simulation()
            self._json_response({'ok': ok, 'message': msg})
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def translate_path(self, path):
        # Serve files from web/ directory
        if self._web_dir:
            import urllib.parse
            path = urllib.parse.unquote(path.split('?', 1)[0].split('#', 1)[0])
            path = path.lstrip('/')
            return os.path.join(self._web_dir, path)
        return super().translate_path(path)

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(length).decode() if length else ''

    def _json_response(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self._cors_headers()
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, format, *args):
        msg = str(args[0]) if args else ''
        if '/api/status' not in msg:
            super().log_message(format, *args)


def main():
    parser = argparse.ArgumentParser(description='Spike Ensemble Server')
    parser.add_argument('--port', type=int, default=8080, help='HTTP port (default: 8080)')
    args = parser.parse_args()

    web_dir = os.path.join(os.path.dirname(__file__), 'web')
    handler = partial(Handler, web_dir=web_dir)
    server = ThreadedHTTPServer(('0.0.0.0', args.port), handler)

    print(f'Spike Ensemble server: http://localhost:{args.port}')
    print(f'Press Ctrl+C to stop')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down...')
        stop_simulation()
        server.shutdown()


if __name__ == '__main__':
    main()
