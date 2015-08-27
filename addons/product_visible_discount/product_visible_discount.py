# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
        field_name = 'list_price'
        currency_id = None
        if res_dict.get(pricelist):
            rule_id = res_dict[pricelist][1]
        else:
            rule_id = False
        if rule_id:
            item_base = item_obj.browse(cr, uid, rule_id, context=context).base
            if item_base == 'list_price':
                field_name = 'list_price'
            if item_base == 'standard_price':
                field_name = 'standard_price'
            currency_id = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.currency_id.id

        product = product_obj.browse(cr, uid, product_id, context=context)
        if not currency_id:
            currency_id = product.company_id.currency_id.id
        factor = 1.0
        if uom and uom != product.uom_id.id:
            # the unit price is in a different uom
            factor = self.pool['product.uom']._compute_price(cr, uid, uom, 1.0, product.uom_id.id)
        return product[field_name] * factor, currency_id

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False,
            fiscal_position_id=False, flag=False, context=None):
        res=super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty,
            uom, qty_uos, uos, name, partner_id,
            lang, update_tax, date_order, packaging=packaging, fiscal_position_id=fiscal_position_id, flag=flag, context=context)

        if context is None:
            context = {}
        context_partner = dict(context, lang=lang, partner_id=partner_id)
        result=res['value']
        pricelist_obj=self.pool.get('product.pricelist')
        product_obj = self.pool.get('product.product')
        if product and pricelist and self.pool.get('res.users').has_group(cr, uid, 'sale.group_discount_per_so_line'):
            if result.get('price_unit',False):
                price=result['price_unit']
            else:
                return res
            uom = result.get('product_uom', uom)
            product = product_obj.browse(cr, uid, product, context=context_partner)
            pricelist_context = dict(context_partner, uom=uom, date=date_order)
            list_price = pricelist_obj.price_rule_get(cr, uid, [pricelist],
                    product.id, qty or 1.0, partner_id, context=pricelist_context)

            so_pricelist = pricelist_obj.browse(cr, uid, pricelist, context=context_partner)

            new_list_price, currency_id = self._get_real_price_currency(cr, uid, product.id, list_price, qty, uom, pricelist, context=context_partner)
            if so_pricelist.discount_policy == 'without_discount' and list_price[pricelist][0] != 0 and new_list_price != 0:
                if product.company_id and so_pricelist.currency_id.id != product.company_id.currency_id.id:
                    # new_list_price is in company's currency while price in pricelist currency
                    ctx = dict(context_partner, date=date_order)
                    new_list_price = self.pool['res.currency'].compute(cr, uid,
                        currency_id, so_pricelist.currency_id.id,
                        new_list_price, context=ctx)
                discount = (new_list_price - price) / new_list_price * 100
                if discount > 0:
                    result['price_unit'] = new_list_price
                    result['discount'] = discount
                else:
                    result['discount'] = 0.0
            else:
                result['discount'] = 0.0
        else:
            result['discount'] = 0.0
        return res
