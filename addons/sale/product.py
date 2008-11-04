# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
from tools import config



class product_product(osv.osv):
    _name = 'product.product'
    _inherit = 'product.product'

    def _pricelist_calculate(self, cr, uid, ids, name, arg, context=None):
        result = {}
        format=""
        pricelist_obj=self.pool.get('product.pricelist')
        if name=='pricelist_purchase':
            pricelist_ids=pricelist_obj.search(cr,uid,[('type','=','purchase')])
        else:
            pricelist_ids=pricelist_obj.search(cr,uid,[('type','=','sale')])
        pricelist_browse=pricelist_obj.browse(cr,uid,pricelist_ids)
        for product in self.browse(cr, uid, ids, context):
            for pricelist in pricelist_browse:
                for version in pricelist.version_id:
                    for items in version.items_id:
                        qty=items.min_quantity
                        price=pricelist_obj.price_get(cr, uid,[pricelist.id],product.id,qty,partner=None, context=None)
                        if name=='pricelist_purchase':
                            format+=pricelist.name + "\t"  +str(qty) +" \t\t" + str(price[pricelist.id]) + "\n"
                        else:
                            format+=pricelist.name + "\t\t\t"  +str(qty) +" \t\t\t" + str(price[pricelist.id]) + "\n"
                    result[product.id]=format
                    format=""
        return result

    _columns = {
        'pricelist_sale':fields.function(
            _pricelist_calculate,
            method=True,
            string='Sale Pricelists',
            type="text"),
        'pricelist_purchase':fields.function(
            _pricelist_calculate,
            method=True,
            string='Purchase Pricelists',
            type="text"),
    }

product_product()
