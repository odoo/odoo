# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import fields, models, _
from odoo.exceptions import UserError
from lxml.etree import ParserError


class IrActionReport(models.Model):
    _inherit = 'ir.actions.report'

    device_ids = fields.Many2many('iot.device', string='IoT Devices', domain="[('type', '=', 'printer')]",
                                help='When setting a device here, the report will be printed through this device on the IoT Box')

    def render_and_send(self, devices, res_ids, data=None, print_id=0, websocket=True):
        """
            Send the dictionary in message to the iot_box via websocket, or return the data to be sent by longpolling.
        """
        data_base64 = self.env.context.get('data_base64', False)
        if not data_base64:
            datas = self._render(self.report_name, res_ids, data=data)
            data_bytes = datas[0]
            data_base64 = base64.b64encode(data_bytes)

        if not websocket:
            return [
                [
                    self.env["iot.box"].search([("identifier", "=", device["iotIdentifier"])]).ip,
                    device["identifier"],
                    device['name'],
                    data_base64,
                    f"{print_id}_{device['id']}",  # idempotent id
                ]
                for device in devices
            ]

        for device in devices:
            self._send_websocket({
                "iotDevice": {
                    "iotIdentifiers": [device["iotIdentifier"]],
                    "identifiers": [{
                        "identifier": device["identifier"],
                        "id": device["id"]
                    }],
                },
                "iot_identifier": device["iotIdentifier"],  # compatibility w/ newer IoT boxes
                "device_identifier": device["identifier"],  # compatibility w/ newer IoT boxes
                "iot_idempotent_id": f"{print_id}_{device['id']}",
                "print_id": print_id,
                "session_id": print_id,  # compatibility w/ newer IoT boxes
                "document": data_base64
            })
        return print_id

    def _send_websocket(self, message):
        """
            Send the dictionnary in message to the iot_box via websocket and return True.
        """
        self.env['bus.bus']._sendone(self.env['iot.channel'].get_iot_channel(), 'iot_action', message)
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

    def get_action_wizard(self):
        self.ensure_one()
        wizard = self.env['select.printers.wizard'].create({
            'display_device_ids' : self.device_ids,
        })
        return {
            'name': _("Select Printers for %s", self.name),
            'res_id': wizard.id,
            'type': 'ir.actions.act_window',
            'res_model': 'select.printers.wizard',
            'target': 'new',
            'views': [[False, 'form']],
            'context': {
                'report_id': self.id,
            },
        }

    def get_devices_from_ids(self, id_list):
        device_ids = self.env['iot.device'].browse(id_list)
        if len(id_list) != len(device_ids.exists()):
            raise UserError(_("One of the printer used to print document have been removed. Please retry the operation to choose new printers to print."))
        device_list = []
        for device_id in device_ids:
            device_list.append({
                "id": device_id.id,
                "identifier": device_id.identifier,
                "name": device_id.name,
                "iotIdentifier": device_id.iot_id.identifier,
                "display_name": device_id.display_name
            })
        return device_list

    def _render_qweb_pdf(self, report_ref, *args, **kwargs):
        """Override to ensure the user is informed when trying to print an empty report
        without an IoT printer.

        This can happen when trying to print delivery labels, that have empty reports used for assigning
        IoT printers.
        """
        try:
            return super()._render_qweb_pdf(report_ref, *args, **kwargs)
        except ParserError:
            raise UserError(_(
                "The report you are trying to print requires an IoT Box to be printed.\n"
                "Make sure you linked the report '%s' to the corresponding IoT printer device.",
                report_ref
            ))
