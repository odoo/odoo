# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('event_booth_ids')
    def _compute_name_short(self):
        wbooth = self.filtered(lambda line: line.event_booth_pending_ids)
        for record in wbooth:
            record.name_short = record.event_booth_pending_ids.event_id.name
        super(SaleOrderLine, self - wbooth)._compute_name_short()

    def _must_drop_from_cart(self):
        """Override of `website_sale` to keep booth lines, as booth products aren't published."""
        return super()._must_drop_from_cart() and not self.event_booth_registration_ids
