# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv import expression


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # ----------------
    # Business methods
    # ----------------

    def _get_sale_tax_filter_domain(self):
        """ Extend the filter to ensure we only get taxes with a type_tax_use of sale, as there could be withholding taxes on the product. """
        # EXTEND account
        filter_domain = super()._get_sale_tax_filter_domain()
        return expression.AND([
            filter_domain,
            [('type_tax_use', '=', 'sale')],
        ])

    def _get_purchase_tax_filter_domain(self):
        """ Extend the filter to ensure we only get taxes with a type_tax_use of purchase, as there could be withholding taxes on the product. """
        # EXTEND account
        filter_domain = super()._get_sale_tax_filter_domain()
        return expression.AND([
            filter_domain,
            [('type_tax_use', '=', 'purchase')],
        ])
