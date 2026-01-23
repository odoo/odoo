# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from uuid import uuid4


class LoyaltyCard(models.Model):
    _name = 'loyalty.card'
    _inherit = 'loyalty.card'

    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)
    source_pos_order_uuid = fields.Char(string='Source PoS Order Uuid', readonly=True, copy=False)

    def _load_pos_self_data_fields(self, config):
        return super()._load_pos_self_data_fields(config) + ['uuid']

    def _is_valid_for_order(self, order):
        self.ensure_one()
        # Check expiration date
        if self.expiration_date and self.expiration_date < fields.Date.context_today(self):
            return False
        # Check partner
        if self.partner_id != order.partner_id:
            return False
        # Check order
        return (not self.source_pos_order_id and not self.source_pos_order_uuid)\
            or (self.source_pos_order_uuid and self.source_pos_order_uuid == order.uuid)\
            or (self.source_pos_order_id and self.source_pos_order_id == order)
