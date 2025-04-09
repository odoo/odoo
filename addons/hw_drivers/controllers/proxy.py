# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.hw_drivers.tools import route

proxy_drivers = {}

class ProxyController(http.Controller):
    @route.iot_route('/hw_proxy/hello', type='http', cors='*')
    def hello(self):
        return "ping"

    @route.iot_route('/hw_proxy/handshake', type='jsonrpc', cors='*')
    def handshake(self):
        return True

    @route.iot_route('/hw_proxy/status_json', type='jsonrpc', cors='*')
    def status_json(self):
        statuses = {}
        for driver in proxy_drivers:
            statuses[driver] = proxy_drivers[driver].get_status()
        return statuses
