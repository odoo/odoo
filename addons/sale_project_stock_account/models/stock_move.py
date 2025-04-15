# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.fields import Domain


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_valid_moves_domain(self):
        domain = super()._get_valid_moves_domain()
        # If anglo-saxon accounting enabled: we do not generate AALs for the reinvoiced products
        if self.env.user.company_id.anglo_saxon_accounting:
            domain = Domain.AND([domain, [('product_id.expense_policy', 'not in', ('sales_price', 'cost'))]])
        return domain
