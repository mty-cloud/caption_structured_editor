#!/usr/bin/env python3
"""桥接服务器 — 替代 python -m http.server，增加书签桥接 API"""

import http.server
import json
import os
import urllib.parse

DIR = os.path.dirname(os.path.abspath(__file__))
bridge_data = {}
bridge_data_lock = False


class Handler(http.server.SimpleHTTPRequestHandler):

    def do_POST(self):
        global bridge_data, bridge_data_lock
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/bridge':
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw)
                bridge_data = data
                bridge_data_lock = True
                self.send_json({'ok': True, 'task_id': data.get('task_id')})
            except Exception as e:
                self.send_json({'ok': False, 'error': str(e)}, 400)
            return
        self.send_error(404)

    def do_GET(self):
        global bridge_data, bridge_data_lock
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/check-bridge':
            if bridge_data_lock:
                d = bridge_data
                bridge_data = {}
                bridge_data_lock = False
                self.send_json(d)
            else:
                self.send_json(None)
            return
        return super().do_GET()

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def translate_path(self, path):
        p = super().translate_path(path)
        if os.path.isfile(p):
            return p
        # 默认返回 index.html
        if not os.path.splitext(p)[1]:
            p = os.path.join(p, 'index.html')
        if not os.path.isfile(p):
            p = os.path.join(DIR, 'index.html')
        return p


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    server = http.server.HTTPServer(('127.0.0.1', port), Handler)
    print(f'🌐 服务已启动：http://localhost:{port}')
    print(f'📡 桥接 API 就绪')
    server.serve_forever()
