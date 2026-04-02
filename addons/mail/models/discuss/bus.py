# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.bus.models.bus import SKIP_NOTIFICATION
from odoo.addons.mail.tools.discuss import Store


class BusBus(models.Model):
    _inherit = "bus.bus"

    def _prepare_payload(self, payload):
        if isinstance(payload, Store):
            return payload.as_dict() or SKIP_NOTIFICATION
        return super()._prepare_payload(payload)
