# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False,
            fiscal_position_id=False, flag=False, context=None):

        def get_real_price_curency(res_dict, product_id, qty, uom, pricelist):
            """Retrieve the price before applying the pricelist"""
            item_obj = self.pool.get('product.pricelist.item')
            price_type_obj = self.pool.get('product.price.type')
            product_obj = self.pool.get('product.product')
            field_name = 'list_price'
            rule_id = res_dict.get(pricelist) and res_dict[pricelist][1] or False
            currency_id = None
            if rule_id:
                item_base = item_obj.read(cr, uid, [rule_id], ['base'])[0]['base']
                if item_base > 0:
                    price_type = price_type_obj.browse(cr, uid, item_base)
                    field_name = price_type.field
                    currency_id = price_type.currency_id

            product = product_obj.browse(cr, uid, product_id, context)
            product_read = product_obj.read(cr, uid, [product_id], [field_name], context=context)[0]

            if not currency_id:
                currency_id = product.company_id.currency_id.id
            factor = 1.0
            if uom and uom != product.uom_id.id:
                # the unit price is in a different uom
                factor = self.pool['product.uom']._compute_qty(cr, uid, uom, 1.0, product.uom_id.id)
            return product_read[field_name] * factor, currency_id

        def get_real_price(res_dict, product_id, qty, uom, pricelist):
            return get_real_price_curency(res_dict, product_id, qty, uom, pricelist)[0]


        res=super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty,
            uom, qty_uos, uos, name, partner_id,
            lang, update_tax, date_order, packaging=packaging, fiscal_position_id=fiscal_position_id, flag=flag, context=context)

        context = {'lang': lang, 'partner_id': partner_id}
        result=res['value']
        pricelist_obj=self.pool.get('product.pricelist')
        product_obj = self.pool.get('product.product')
        if product and pricelist and self.pool.get('res.users').has_group(cr, uid, 'sale.group_discount_per_so_line'):
            if result.get('price_unit',False):
                price=result['price_unit']
            else:
                return res
            uom = result.get('product_uom', uom)
            product = product_obj.browse(cr, uid, product, context)
            pricelist_context = dict(context, uom=uom, date=date_order)
            list_price = pricelist_obj.price_rule_get(cr, uid, [pricelist],
                    product.id, qty or 1.0, partner_id, context=pricelist_context)

            so_pricelist = pricelist_obj.browse(cr, uid, pricelist, context=context)

            new_list_price, currency_id = get_real_price_curency(list_price, product.id, qty, uom, pricelist)
            if so_pricelist.visible_discount and list_price[pricelist][0] != 0 and new_list_price != 0:
                if product.company_id and so_pricelist.currency_id.id != product.company_id.currency_id.id:
                    # new_list_price is in company's currency while price in pricelist currency
                    ctx = context.copy()
                    ctx['date'] = date_order
                    new_list_price = self.pool['res.currency'].compute(cr, uid,
                        currency_id.id, so_pricelist.currency_id.id,
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
