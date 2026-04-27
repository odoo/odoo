# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('website_id')
    def _compute_l10n_br_presence(self):
        # Override.
        super()._compute_l10n_br_presence()
        for order in self:
            if order.website_id:
                order.l10n_br_presence = '2'

    def _prepare_invoice(self):
        # Override
        res = super()._prepare_invoice()
        res['l10n_br_presence'] = self.l10n_br_presence
        return res
