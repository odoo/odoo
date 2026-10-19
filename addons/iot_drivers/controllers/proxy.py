# TODO: remove this file when v19.0 is deprecated (/hw_proxy/hello still used in v19.0)

from odoo import http
from odoo.addons.iot_drivers.tools import route


class ProxyController(http.Controller):
    @route.iot_route('/hw_proxy/hello', type='http', cors='*')
    def hello(self):
        return "ping"
