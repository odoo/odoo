# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2015 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import json
import logging
import urllib2
import websocket
from threading import Lock

import openerp
from openerp import http

_logger = logging.getLogger(__name__)

class HardwareScreen(openerp.addons.web.controllers.main.Home):
    def __init__(self):
        self.chromium_websocket_lock = Lock()
        self.chromium_connection = None

    def _open_chromium_connection(self):
        # locally running chromium with --remote-debugging-port=9222
        url = 'http://localhost:9222/json'

        resp = urllib2.urlopen(url).read()
        resp = json.loads(resp)

        websocket_address = resp[0]['webSocketDebuggerUrl']
        _logger.info('opening websocket address: %s' % websocket_address)

        return websocket.create_connection(websocket_address)

    @http.route('/hw_proxy/customer_facing_display', type='json', auth='none', cors='*')
    def update_user_facing_display(self, html):
        # chromium only supports one remote debugging client per websocket,
        # so make sure we don't try to handle multiple requests at the same time
        with self.chromium_websocket_lock:
            if not self.chromium_connection:
                self.chromium_connection = self._open_chromium_connection()

            # quoting is a bit tricky, single quotes are used inside the evaled
            # js and double quotes are used inside the JSON, so quotes inside of the
            # html need to all turn into an escaped " which is \\"
            html = html.replace('"', '\\"')
            html = html.replace("'", '\\"')

            # newlines are illegal tokens in javascript strings
            html = html.replace('\n', ' ')

            js_to_eval = "var doc = document.open('text/html', 'replace'); doc.write('%s'); doc.close();" % html

            request = '{"id": 1, "method": "Runtime.evaluate", "params": {"expression": "%s" }}' % js_to_eval
            self.chromium_connection.send(request)
