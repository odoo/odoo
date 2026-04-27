import logging
from odoo import models
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class IrActionReport(models.Model):
    _inherit = 'ir.actions.report'

    def render_and_send(self, devices, res_ids, data=None, print_id=0, websocket=True):
        """
            Send the dictionary in message to the iot_box via websocket, or return the data to be sent by longpolling.
        """
        # only override the method for delivery_iot reports
        if self.report_name not in ['delivery_iot.report_shipping_labels', 'delivery_iot.report_shipping_docs']:
            return super().render_and_send(devices, res_ids, data=data, print_id=print_id, websocket=websocket)

        domain = [('res_model', '=', 'stock.picking'), ('res_id', 'in', res_ids)]
        if self.report_name == 'delivery_iot.report_shipping_labels':
            domain = expression.AND([domain, [('name', 'ilike', 'Label%')]])
        elif self.report_name == 'delivery_iot.report_shipping_docs':
            domain = expression.AND([domain, [('name', 'ilike', 'ShippingDoc%')]])

        attachments = self.env['ir.attachment'].search(domain, order='id desc')
        if not attachments:
            _logger.warning("No attachment found for report %s and res_ids %s", self.report_name, res_ids)
            return []

        if not websocket:
            return [
                [
                    self.env["iot.box"].search([("identifier", "=", device["iotIdentifier"])]).ip,
                    device["identifier"],
                    device['name'],
                    attachment.datas,
                    f"{print_id}_{attachment.id}_{device['id']}",  # idempotent id
                ]
                for attachment in attachments
                for device in devices
            ]

        for device in devices:
            for attachment in attachments:
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
                    "iot_idempotent_id": f"{print_id}_{attachment.id}_{device['id']}",
                    "print_id": print_id,
                    "session_id": print_id,  # compatibility w/ newer IoT boxes
                    "document": attachment.datas,
                })
        return None
