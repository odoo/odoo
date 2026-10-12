# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.fields import Domain


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_valid_moves_domain(self):
        domain = super()._get_valid_moves_domain()
        # No AAL for the reinvoiced products of a company using anglo-saxon accounting
        return Domain.AND([domain, Domain.OR([
            [('company_id.anglo_saxon_accounting', '=', False)],
            [('product_id.reinvoice_policy', 'not in', ('sales_price', 'cost'))],
        ])])
