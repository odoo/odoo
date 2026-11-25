# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
import socket
import threading
import time
from unittest.mock import patch

import requests

from odoo.service.server import ThreadedWSGIServerReloadable
from odoo.tests.common import BaseCase, tagged
from odoo.tools import config


def application(environ, start_response):
    path = environ['PATH_INFO']
    if path == '/web/health':
        start_response('200 OK', [])
        return [b'pass']
    if path == '/upload':
        data = environ['wsgi.input'].read()
        start_response('200 OK', [])
        return [b'received %d' % len(data)]
    # answer without reading the request body
    start_response('400 Bad Request', [('Content-Length', '0')])
    return []


@tagged('-at_install', 'post_install')
class TestThreadedServer(BaseCase):

    def setUp(self):
        super().setUp()
        self.startPatcher(patch.dict(os.environ, {'ODOO_MAX_HTTP_THREADS': '2', 'ODOO_HTTP_SOCKET_TIMEOUT': '0.5'}))
        # use the production timeout, not the one of the test mode
        self.startPatcher(patch.dict(config.options, {'test_enable': False, 'test_file': False}))
        self.server = ThreadedWSGIServerReloadable('127.0.0.1', 0, application)
        self.url = 'http://127.0.0.1:%d' % self.server.server_port
        server_thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.05})
        server_thread.start()
        self.addCleanup(server_thread.join)
        self.addCleanup(self.server.shutdown)

    def assertHealthy(self):
        self.assertEqual(requests.get(self.url + '/web/health', timeout=10).text, 'pass')

    def test_unread_request_body(self):
        for _ in range(2):  # as many as ODOO_MAX_HTTP_THREADS
            response = requests.post(self.url, data=b'A' * 20_000, stream=True, timeout=10)
            self.addCleanup(response.close)
            self.assertEqual(response.status_code, 400)
        self.assertHealthy()

    def test_idle_connection(self):
        sock = socket.create_connection(self.server.server_address, timeout=3)
        self.addCleanup(sock.close)
        self.assertEqual(sock.recv(1), b'')  # closed by the server
        self.assertHealthy()

    def test_slow_upload(self):
        def slow_body():
            for _ in range(5):
                time.sleep(0.2)
                yield b'A' * 1000

        response = requests.post(self.url + '/upload', data=slow_body(), timeout=10)
        self.assertEqual(response.text, 'received 5000')
