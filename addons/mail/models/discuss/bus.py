# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.bus.models.bus import SKIP_NOTIFICATION
from odoo.addons.mail.tools.discuss import Store


class BusBus(models.Model):
    _inherit = "bus.bus"

    def _ensure_hooks(self):
        # precommit data lives exactly as long as the batch, which is when the payloads are built
        self.env.cr.precommit.data.setdefault("mail.store.field_lists", {})
        return super()._ensure_hooks()

    def _prepare_payload(self, payload):
        if isinstance(payload, Store):
            if not payload._auto_send:
                return SKIP_NOTIFICATION
            return payload.as_dict() or SKIP_NOTIFICATION
        return super()._prepare_payload(payload)
