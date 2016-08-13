# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class StockChangeStandardPrice(models.TransientModel):
    _name = "stock.change.standard.price"
    _description = "Change Standard Price"

    new_price = fields.Float(
        'Price', digits=dp.get_precision('Product Price'),  required=True,
        help="If cost price is increased, stock variation account will be debited "
             "and stock output account will be credited with the value = (difference of amount * quantity available).\n"
             "If cost price is decreased, stock variation account will be creadited and stock input account will be debited.")
    counterpart_account_id = fields.Many2one(
        'account.account', string="Counter-Part Account",
        domain=[('deprecated', '=', False)], required=True)

    @api.model
    def default_get(self, fields):
        res = super(StockChangeStandardPrice, self).default_get(fields)

        product_or_template = self.env[self._context['active_model']].browse(self._context['active_id'])
        if 'new_price' in fields and 'default_new_price' not in res:
            res['new_price'] = product_or_template.standard_price
        if 'counterpart_account_id' in fields and 'counterpart_account_id' not in res:
            res['counterpart_account_id'] = product_or_template.property_account_expense_id.id or product_or_template.categ_id.property_account_expense_categ_id.id
        return res

    @api.multi
    def change_price(self):
        """ Changes the Standard Price of Product and creates an account move accordingly. """
        self.ensure_one()
        if self._context['active_model'] == 'product.template':
            products = self.env['product.template'].browse(self._context['active_id']).product_variant_ids
        else:
            products = self.env['product.product'].browse(self._context['active_id'])

        products.do_change_standard_price(self.new_price, self.counterpart_account_id.id)
        return {'type': 'ir.actions.act_window_close'}
