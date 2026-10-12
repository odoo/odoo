# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ['event_ticket_id', 'event_slot_id']
