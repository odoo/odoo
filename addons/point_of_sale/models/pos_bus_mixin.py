# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
from odoo import fields, models, api


class PosBusMixin(models.AbstractModel):
    _name = 'pos.bus.mixin'
    _description = "Bus Mixin"

    access_token = fields.Char('Security Token', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._ensure_access_token()
        return records

    def _ensure_access_token(self):
        if self.access_token:
            return self.access_token
        token = self.access_token = str(uuid.uuid4())
        return token

    def _notify(self, *notifications, private=True) -> None:
        """ Send a notification to the bus.
        ex: one notification: ``self._notify('STATUS', {'status': 'closed'})``
        multiple notifications: ``self._notify(('STATUS', {'status': 'closed'}), ('TABLE_ORDER_COUNT', {'count': 2}))``
        """
        self.ensure_one()
        self._ensure_access_token()
        if isinstance(notifications[0], str):
            if len(notifications) != 2:
                raise ValueError("If you want to send a single notification, you must provide a name: str and a message: any")
            notifications = [notifications]
        for name, message in notifications:
            self.env["bus.bus"]._sendone(
                self.access_token, f"{self.access_token}-{name}" if private else name, message
            )
