# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api
from openerp.osv import fields, osv
from openerp.tools.translate import _

class product_pricelist(osv.osv):
    _inherit = 'product.pricelist'

    _columns ={
        'visible_discount': fields.boolean('Visible Discount'),
    }
    _defaults = {
         'visible_discount': True,
    }


class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    def get_real_price_currency(self, cr, uid, product_id, res_dict, qty, uom, pricelist, context=None):
        """Retrieve the price before applying the pricelist"""
        item_obj = self.pool['product.pricelist.item']
        price_type_obj = self.pool['product.price.type']
        product_obj = self.pool['product.product']
        field_name = 'list_price'
        if res_dict.get(pricelist):
            rule_id = res_dict[pricelist][1]
        else:
            rule_id = False
        if rule_id:
            item_base = item_obj.browse(cr, uid, rule_id, context=context).base
            if item_base > 0:
                price_type = price_type_obj.browse(cr, uid, item_base)
                field_name = price_type.field
                currency_id = price_type.currency_id.id

        product = product_obj.browse(cr, uid, product_id, context=context)
        if not currency_id:
            currency_id = product.company_id.currency_id.id
        factor = 1.0
        if uom and uom != product.uom_id.id:
            # the unit price is in a different uom
            factor = self.pool['product.uom']._compute_qty(cr, uid, uom, 1.0, product.uom_id.id)
        return product[field_name] * factor, currency_id

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(sale_order_line, self).product_id_change()
        context_partner = dict(self.env.context, partner_id=self.order_id.partner_id.id)
        if self.product_id and self.order_id.pricelist_id and self.env.user.has_group('sale.group_discount_per_so_line'):
            pricelist_context = dict(context_partner, uom=self.product_uom.id, date=self.order_id.date_order)
            list_price = self.order_id.pricelist_id.with_context(pricelist_context).price_rule_get(self.product_id.id, self.product_uom_qty or 1.0, self.order_id.partner_id)

            new_list_price, currency_id = self.with_context(context_partner).get_real_price_currency(self.product_id.id, list_price, self.product_uom_qty, self.product_uom.id, self.order_id.pricelist_id.id)
            if self.order_id.pricelist_id.visible_discount and list_price[self.order_id.pricelist_id.id][0] != 0 and new_list_price != 0:
                if self.product_id.company_id and self.order_id.pricelist_id.currency_id.id != self.product_id.company_id.currency_id.id:
                    # new_list_price is in company's currency while price in pricelist currency
                    ctx = dict(context_partner, date=self.order_id.date_order)
                    new_list_price = self.env['res.currency'].browse(currency_id).with_context(ctx).compute(new_list_price, self.order_id.pricelist_id.currency_id.id)
                discount = (new_list_price - self.price_unit) / new_list_price * 100
                if discount > 0:
                    self.price_unit = new_list_price
                    self.discount = discount
                else:
                    self.discount = 0.0
            else:
                self.discount = 0.0
        else:
            self.discount = 0.0
        return res

    @api.onchange('product_uom')
    def product_uom_change(self):
        res = super(sale_order_line, self).product_uom_change()
        if not self.product_uom:
            self.price_unit = 0.0
            return
        if self.order_id.pricelist_id and self.order_id.partner_id and self.env.user.has_group('sale.group_discount_per_so_line'):
            context_partner = dict(self.env.context, partner_id=self.order_id.partner_id.id)
            pricelist_context = dict(context_partner, uom=self.product_uom.id, date=self.order_id.date_order)
            list_price = self.order_id.pricelist_id.with_context(pricelist_context).price_rule_get(self.product_id.id, self.product_uom_qty or 1.0, self.order_id.partner_id)
            new_list_price, currency_id = self.with_context(context_partner).get_real_price_currency(self.product_id.id, list_price, self.product_uom_qty, self.product_uom.id, self.order_id.pricelist_id.id)
            if self.order_id.pricelist_id.visible_discount and list_price[self.order_id.pricelist_id.id][0] != 0 and new_list_price != 0:
                if self.product_id.company_id and self.order_id.pricelist_id.currency_id.id != self.product_id.company_id.currency_id.id:
                    # new_list_price is in company's currency while price in pricelist currency
                    ctx = dict(context_partner, date=self.order_id.date_order)
                    new_list_price = self.env['res.currency'].browse(currency_id).with_context(ctx).compute(new_list_price, self.order_id.pricelist_id.currency_id.id)
                discount = (new_list_price - self.price_unit) / new_list_price * 100
                if discount > 0:
                    self.price_unit = new_list_price
                    self.discount = discount
                else:
                    self.discount = 0.0
            else:
                self.discount = 0.0
        else:
            self.discount = 0.0
        return res
