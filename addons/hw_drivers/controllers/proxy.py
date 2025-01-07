from odoo import http
from odoo.addons.hw_drivers.main import iot_devices

class ProxyController(http.Controller):
    @http.route('/hw_proxy/hello', type='http', auth='none', cors='*')
    def hello(self):
        return "ping"

    @http.route('/hw_proxy/status_json', type='jsonrpc', auth='none', cors='*')
    def status_json(self):
        return {
            device_name: device.get_status()
            for device_name, device in iot_devices.items()
            if device.device_type in ['printer', 'scale', 'scanner']
        }
