# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import fields, models


class IrActionReport(models.Model):
    _inherit = 'ir.actions.report'

    device_ids = fields.Many2many('iot.device', string='IoT Devices', domain="[('type', '=', 'printer')]",
                                help='When setting a device here, the report will be printed through this device on the IoT Box')

    def render_and_send(self, devices, res_ids, data=None, print_id=0):
        """
            Send the dictionnary in message to the iot_box via websocket.
        """
        datas = self._render(self.report_name, res_ids, data=data)
        data_bytes = datas[0]
        data_base64 = base64.b64encode(data_bytes)
        iot_identifiers = {device["iotIdentifier"] for device in devices}
        self._send_websocket({
            'iotDevice': {
                "iotIdentifiers": list(iot_identifiers),
                "identifiers": [{
                    "identifier" : device["identifier"],
                    "id" : device["id"]
                } for device in devices],
            },
            'print_id' : print_id,
            'document': data_base64
        })
        return print_id

    def _send_websocket(self, message):
        """
            Send the dictionnary in message to the iot_box via websocket and return True.
        """
        self.env['bus.bus']._sendone(self.env['iot.channel'].get_iot_channel(), 'print', message)
        return True

    def report_action(self, docids, data=None, config=True):
        result = super(IrActionReport, self).report_action(docids, data, config)
        if result.get('type') != 'ir.actions.report':
            return result
        device = self.device_ids and self.device_ids[0]
        if data and data.get('device_id'):
            device = self.env['iot.device'].browse(data['device_id'])

        result['id'] = self.id
        result['device_ids'] = device.mapped('identifier')
        return result

    def _get_readable_fields(self):
        return super()._get_readable_fields() | {
            "device_ids",
        }

    def get_action_wizard(self, res_ids, data=None, print_id=0):
        wizard = self.env['select.printers.wizard'].create({
            'display_device_ids' : self.device_ids,
        })
        return {
                'name': "Select printers",
                'res_id': wizard.id,
                'type': 'ir.actions.act_window',
                'res_model': 'select.printers.wizard',
                'target': 'new',
                'views': [[False, 'form']],
                'context' : {
                    'res_ids' : res_ids,
                    'data' : data,
                    'report_id' : self._ids[0],
                    'print_id' : print_id,
                    'default_report_id' : self._ids[0]
                },
        }

    def get_devices_from_ids(self, id_list):
        device_list = []
        device_ids = self.env['iot.device'].browse(id_list)
        for device_id in device_ids:
            device_list.append({"id": device_id.id, "identifier": device_id.identifier, "name": device_id.name, "iotIdentifier": device_id.iot_id.identifier})
        return device_list
