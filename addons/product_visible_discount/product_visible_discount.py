# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api
from openerp.osv import fields, osv
from openerp.tools.translate import _

class product_pricelist(osv.osv):
    _inherit = 'product.pricelist'

    _columns = {
        'discount_policy': fields.selection([('with_discount', 'Discount included in the price'), ('without_discount', 'Show discount in the sale order')], string="Discount Policy"),
    }
    _defaults = {'discount_policy': 'with_discount'}


class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    def _get_real_price_currency(self, cr, uid, product_id, res_dict, qty, uom, pricelist, context=None):
        """Retrieve the price before applying the pricelist"""
        item_obj = self.pool['product.pricelist.item']
        product_obj = self.pool['product.product']
        field_name = 'lst_price'
        currency_id = None
        if res_dict.get(pricelist):
            rule_id = res_dict[pricelist][1]
        else:
            rule_id = False
        if rule_id:
            item = item_obj.browse(cr, uid, rule_id, context=context)
            if item.base == 'standard_price':
                field_name = 'standard_price'
            currency_id = item.pricelist_id.currency_id.id

        product = product_obj.browse(cr, uid, product_id, context=context)
        if not currency_id:
            currency_id = product.company_id.currency_id.id
        factor = 1.0
        if uom and uom != product.uom_id.id:
            # the unit price is in a different uom
            factor = self.pool['product.uom']._compute_price(cr, uid, uom, 1.0, product.uom_id.id)
        return product[field_name] * factor, currency_id

    @api.onchange('product_id', 'price_unit', 'product_uom', 'product_uom_qty', 'tax_id')
    def _onchange_discount(self):
        self.discount = 0.0
        if not (self.product_id and self.product_uom
                and self.order_id.partner_id and self.order_id.pricelist_id
                and self.order_id.pricelist_id.discount_policy == 'without_discount'
                and self.env.user.has_group('sale.group_discount_per_so_line')):
            return

        context_partner = dict(self.env.context, partner_id=self.order_id.partner_id.id)
        pricelist_context = dict(context_partner, uom=self.product_uom.id, date=self.order_id.date_order)

        list_price = self.order_id.pricelist_id.with_context(pricelist_context).price_rule_get(self.product_id.id, self.product_uom_qty or 1.0, self.order_id.partner_id)
        new_list_price, currency_id = self.with_context(context_partner)._get_real_price_currency(self.product_id.id, list_price, self.product_uom_qty, self.product_uom.id, self.order_id.pricelist_id.id)
        new_list_price = self.env['account.tax']._fix_tax_included_price(new_list_price, self.product_id.taxes_id, self.tax_id)

        if list_price[self.order_id.pricelist_id.id][0] != 0 and new_list_price != 0:
            if self.product_id.company_id and self.order_id.pricelist_id.currency_id != self.product_id.company_id.currency_id:
                # new_list_price is in company's currency while price in pricelist currency
                ctx = dict(context_partner, date=self.order_id.date_order)
                new_list_price = self.env['res.currency'].browse(currency_id).with_context(ctx).compute(new_list_price, self.order_id.pricelist_id.currency_id)
            discount = (new_list_price - self.price_unit) / new_list_price * 100
            if discount > 0:
                self.discount = discount
