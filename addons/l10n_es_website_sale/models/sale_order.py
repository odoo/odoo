# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends("website_id")
    def _compute_journal_id(self):
        website_orders = self.filtered(lambda order: order.website_id and not order.journal_id)
        for order in website_orders:
            if order.amount_total < order.company_id.l10n_es_simplified_invoice_limit:
                order.journal_id = order.website_id.simplified_invoice_journal_id
        super(SaleOrder, self - website_orders)._compute_journal_id()
