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

from osv import fields, osv
from tools.translate import _

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
                product_uom_obj = self.pool.get('product.uom')
                uom_data = product_uom_obj.browse(cr, uid,  product.uom_id.id)
                factor = uom_data.factor
            return product_read[field_name] * factor


        res=super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty,
            uom, qty_uos, uos, name, partner_id,
            lang, update_tax, date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=context)

        context = {'lang': lang, 'partner_id': partner_id}
        result=res['value']
        pricelist_obj=self.pool.get('product.pricelist')
        product_obj = self.pool.get('product.product')
        if product:
            if result.get('price_unit',False):
                price=result['price_unit']
            else:
                return res

            product = product_obj.browse(cr, uid, product, context)
            list_price = pricelist_obj.price_get(cr, uid, [pricelist],
                    product.id, qty or 1.0, partner_id, {'uom': uom,'date': date_order })

            pricelists = pricelist_obj.read(cr,uid,[pricelist],['visible_discount'])

            new_list_price = get_real_price(list_price, product.id, qty, uom, pricelist)
            if(len(pricelists)>0 and pricelists[0]['visible_discount'] and list_price[pricelist] != 0):
                discount = (new_list_price - price) / new_list_price * 100
                result['price_unit'] = new_list_price
                result['discount'] = discount
            else:
                result['discount'] = 0.0
        return res

sale_order_line()

class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"

    def product_id_change(self, cr, uid, ids, product, uom, qty=0, name='', type='out_invoice', partner_id=False, fposition_id=False, price_unit=False, currency_id=False, context=None, company_id=None):
        res = super(account_invoice_line, self).product_id_change(cr, uid, ids, product, uom, qty, name, type, partner_id, fposition_id, price_unit,currency_id, context=context, company_id=company_id)

        def get_real_price(res_dict, product_id, qty, uom, pricelist):
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
                product_uom_obj = self.pool.get('product.uom')
                uom_data = product_uom_obj.browse(cr, uid,  product.uom_id.id)
                factor = uom_data.factor
            return product_read[field_name] * factor

        if product:
            pricelist_obj = self.pool.get('product.pricelist')
            partner_obj = self.pool.get('res.partner')
            product = self.pool.get('product.product').browse(cr, uid, product, context=context)
            result = res['value']
            pricelist = False
            real_price = 0.00
            if type in ('in_invoice', 'in_refund'):
                if not price_unit and partner_id:
                    pricelist =partner_obj.browse(cr, uid, partner_id).property_product_pricelist_purchase.id
                    if not pricelist:
                        raise osv.except_osv(_('No Purchase Pricelist Found!'),_("You must first define a pricelist on the supplier form!"))
                    price_unit_res = pricelist_obj.price_get(cr, uid, [pricelist], product.id, qty or 1.0, partner_id, {'uom': uom})
                    price_unit = price_unit_res[pricelist]
                    real_price = get_real_price(price_unit_res, product.id, qty, uom, pricelist)
            else:
                if partner_id:
                    pricelist = partner_obj.browse(cr, uid, partner_id).property_product_pricelist.id
                    if not pricelist:
                        raise osv.except_osv(_('No Sale Pricelist Found!'),_("You must first define a pricelist on the customer form!"))
                    price_unit_res = pricelist_obj.price_get(cr, uid, [pricelist], product.id, qty or 1.0, partner_id, {'uom': uom})
                    price_unit = price_unit_res[pricelist]

                    real_price = get_real_price(price_unit_res, product.id, qty, uom, pricelist)
            if pricelist:
                pricelists=pricelist_obj.read(cr,uid,[pricelist],['visible_discount'])
                if(len(pricelists)>0 and pricelists[0]['visible_discount'] and real_price != 0):
                    discount=(real_price-price_unit) / real_price * 100
                    result['price_unit'] = real_price
                    result['discount'] = discount
                else:
                    result['discount']=0.0
        return res

account_invoice_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
