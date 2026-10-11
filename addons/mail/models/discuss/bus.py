# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial

from odoo import models

from odoo.addons.bus.models.bus import SKIP_NOTIFICATION
from odoo.addons.mail.tools.discuss import Store


class BusBus(models.Model):
    _inherit = "bus.bus"

    def _ensure_hooks(self):
        precommit = self.env.cr.precommit
        if "bus.bus.values" in precommit.data:
            super()._ensure_hooks()
            return
        # Share field lists only while create_bus runs, as precommit hooks run in order
        precommit.add(partial(precommit.data.setdefault, "mail.store.field_lists", {}))
        super()._ensure_hooks()
        precommit.add(partial(precommit.data.pop, "mail.store.field_lists"))

    def _prepare_payload(self, payload):
        if isinstance(payload, Store):
            if not payload._auto_send:
                return SKIP_NOTIFICATION
            return payload.as_dict() or SKIP_NOTIFICATION
        return super()._prepare_payload(payload)
