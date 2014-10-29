# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

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

product_pricelist()

class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False,
            fiscal_position=False, flag=False, context=None):

        def get_real_price(res_dict, product_id, qty, uom, pricelist):
            """Retrieve the price before applying the pricelist"""
            item_obj = self.pool.get('product.pricelist.item')
            price_type_obj = self.pool.get('product.price.type')
            product_obj = self.pool.get('product.product')
            field_name = 'list_price'

            if res_dict.get('item_id',False) and res_dict['item_id'].get(pricelist,False):
                item = res_dict['item_id'].get(pricelist,False)
                item_base = item_obj.read(cr, uid, [item], ['base'])[0]['base']
                if item_base > 0:
                    field_name = price_type_obj.browse(cr, uid, item_base).field

            product = product_obj.browse(cr, uid, product_id, context)
            product_read = product_obj.read(cr, uid, product_id, [field_name], context=context)

            factor = 1.0
            if uom and uom != product.uom_id.id:
                # the unit price is in a different uom
                factor = self.pool['product.uom']._compute_qty(cr, uid, uom, 1.0, product.uom_id.id)
            return product_read[field_name] * factor


        res=super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty,
            uom, qty_uos, uos, name, partner_id,
            lang, update_tax, date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=context)

        context = {'lang': lang, 'partner_id': partner_id}
        result=res['value']
        pricelist_obj=self.pool.get('product.pricelist')
        product_obj = self.pool.get('product.product')
        if product and pricelist:
            if result.get('price_unit',False):
                price=result['price_unit']
            else:
                return res
            uom = result.get('product_uom', uom)
            product = product_obj.browse(cr, uid, product, context)
            list_price = pricelist_obj.price_get(cr, uid, [pricelist],
                    product.id, qty or 1.0, partner_id, {'uom': uom,'date': date_order })

            so_pricelist = pricelist_obj.browse(cr, uid, pricelist, context=context)

            new_list_price = get_real_price(list_price, product.id, qty, uom, pricelist)
            if so_pricelist.visible_discount and list_price[pricelist] != 0 and new_list_price != 0:
                if product.company_id and so_pricelist.currency_id.id != product.company_id.currency_id.id:
                    # new_list_price is in company's currency while price in pricelist currency
                    ctx = context.copy()
                    ctx['date'] = date_order
                    new_list_price = self.pool['res.currency'].compute(cr, uid,
                        product.company_id.currency_id.id, so_pricelist.currency_id.id,
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
