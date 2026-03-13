# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class BusBus(models.Model):
    _inherit = "bus.bus"

    @api.model
    def _sendone(self, target, notification_type, message):
        if mail_store := self.env.context.get("mail_store"):
            mail_store.enqueue_bus_notification(target, notification_type, message)
        else:
            super()._sendone(target, notification_type, message)
