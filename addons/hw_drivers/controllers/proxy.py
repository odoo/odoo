# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import http
from odoo.addons.hw_drivers.main import blackbox_device
from odoo.addons.hw_drivers.iot_handlers.blackbox.helpers import BlackboxError
from odoo.addons.hw_drivers.tools import route
from werkzeug.exceptions import InternalServerError

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

    @route.iot_route('/hw_proxy/l10n_be_pos_fdm', type='jsonrpc', cors='*')
    def l10n_be_pos_fdm(self):
        blackbox_instance = blackbox_device.get('blackbox')
        if not blackbox_instance:
            return {"error": "No blackbox device found"}

        data = {}
        devices = blackbox_instance.blackboxes

        for fdm_id, ser in devices.items():
            data[fdm_id] = ser.transport.serial.port

        return json.dumps(data)

    @route.iot_route('/hw_proxy/l10n_be_pos_fdm/<id>', type='jsonrpc', cors='*')
    def l10n_be_pos_fdm_id(self, id, batch):
        blackbox_instance = blackbox_device.get('blackbox')
        if not blackbox_instance:
            return {"error": "No blackbox device found"}

        try:
            results = []
            for cmd_obj in batch:
                command = cmd_obj.get("command")
                data = cmd_obj.get("data", "")

                if not isinstance(command, str):
                    return "Invalid batch item: missing command.", 400

                resp = blackbox_instance.send(id, command, data)
                results.append(resp)

            return json.dumps({"results": results})
        except BlackboxError as e:
            details = str(e), e.details if e.details else 500
            raise InternalServerError(details)
