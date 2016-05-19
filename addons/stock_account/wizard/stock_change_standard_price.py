# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp


class ChangeStandardPrice(models.TransientModel):
    _name = "stock.change.standard.price"
    _description = "Change Standard Price"

    new_price = fields.Float('Price', required=True, digits_compute=dp.get_precision('Product Price'),
        help="If cost price is increased, stock variation account will be debited "
             "and stock output account will be credited with the value = (difference of amount * quantity available).\n"
             "If cost price is decreased, stock variation account will be creadited and stock input account will be debited.")
    counterpart_account_id = fields.Many2one('account.account', string="Counter-Part Account", required=True, domain=[('deprecated', '=', False)])

    @api.model
    def default_get(self, fields):
        if self.env.context.get("active_model") == 'product.product':
            Product = self.env['product.product']
        else:
            Product = self.env['product.template']
        Product = Product.browse(self.env.context.get('active_id'))
        res = super(ChangeStandardPrice, self).default_get(fields)

        if 'new_price' in fields:
            res['new_price'] = Product.standard_price
        if 'counterpart_account_id' in fields:
            default_account = Product.property_account_expense_id or Product.categ_id.property_account_expense_categ_id
            if default_account:
                res['counterpart_account_id'] = default_account.id
        return res

    @api.multi
    def change_price(self):
        """ Changes the Standard Price of Product.
            And creates an account move accordingly.
        """
        product_id = self.env.context.get('active_id')
        assert product_id, _('Active ID is not set in Context.')
        if self.env.context.get("active_model") == 'product.template':
            products = self.env['product.template'].browse(product_id).product_variant_ids
        else:
            products = self.env['product.product'].browse(product_id)
        products.do_change_standard_price(self.new_price,)
        return {'type': 'ir.actions.act_window_close'}
