# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, models


class SaleAdvancePaymentInv(models.TransientModel):
    """Downpayment should have no taxes set on them.
       To that effect, we should get the category 'Gift card' (10005) on the
       deposit product. If this category cannot be found, either the user
       messed up with TaxCloud categories or did not configure them properly yet;
       in this case, the user is also responsible for configuring this properly.

       Otherwise, taxes are applied on downpayments, but not subtracted from the
       regular invoice, since we ignore negative lines, so get counted twice.
    """
    _inherit = 'sale.advance.payment.inv'

    def _compute_product_id(self):
        super()._compute_product_id()
        dp_products = self.product_id
        deposit_category = self._get_deposit_category()
        if deposit_category and dp_products.tic_category_id != deposit_category:
            dp_products.tic_category_id = deposit_category

    @api.model
    def _get_deposit_category(self):
        return self.env['product.tic.category'].search([('code', '=', '10005')], limit=1)

    def _prepare_down_payment_product_values(self):
        values = super()._prepare_down_payment_product_values()
        values['tic_category_id'] = self._get_deposit_category().id
        return values
