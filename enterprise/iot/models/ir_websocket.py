# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrWebsocket(models.AbstractModel):
    _inherit = 'ir.websocket'

    def _subscribe(self, data):
        mac_address = data.get("mac_address")
        if mac_address:
            iot_box = self.env["iot.box"].sudo().search([("identifier", "=", mac_address)], limit=1)
            if iot_box:
                iot_box.is_websocket_active = True
        return super()._subscribe(data)
