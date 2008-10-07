# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
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
