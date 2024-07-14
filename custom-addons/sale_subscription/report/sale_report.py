# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class SaleReport(models.Model):
    _inherit = 'sale.report'

    def _where_sale(self):
        res = super()._where_sale()
        # Do not add upsell information to the sales report
        # as it will be updated on the original sale order.
        # Note: this analysis may not be accurate because
        # it does not take account of discounts, for example.
        res += """
            AND (
                s.subscription_state IS NULL OR
                s.subscription_state != '7_upsell'
            )
        """
        return res
