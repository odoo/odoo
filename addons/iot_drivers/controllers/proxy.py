# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.iot_drivers.tools import route


class ProxyController(http.Controller):
    @route.iot_route('/hw_proxy/hello', type='http', cors='*')
    def hello(self):
        return "ping"
