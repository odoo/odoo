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

class product_pricelist(osv.osv):
    _inherit = "product.pricelist"
    def _compute_price(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for id in ids:
            res[id]=0.0
        return res
    _columns = {
        'price': fields.function(_compute_price, type='float', method=True, string='Price', digits=(16, int(config['price_accuracy']))),
        }
product_pricelist()

class product_product(osv.osv):
    _name = 'product.product'
    _inherit = 'product.product'

    def _pricelist_sale_ids(self, cr, uid, ids, name, arg, context=None):
        result = {}
        if not context:
            context={}
        pricelist_obj=self.pool.get('product.pricelist')
        for product in self.browse(cr, uid, ids, context):
            pricelist_ids=pricelist_obj.search(cr,uid,[('type','=','sale')], context=context)
            result[product.id]=pricelist_ids
        return result

    def _pricelist_purchase_ids(self, cr, uid, ids, name, arg, context=None):
        result = {}
        pricelist_obj=self.pool.get('product.pricelist')
        for product in self.browse(cr, uid, ids, context):
            pricelist_ids=pricelist_obj.search(cr,uid,[('type','=','purchase')])
            result[product.id]=pricelist_ids
        return result

    _columns = {
        'pricelist_sale':fields.function(
            _pricelist_sale_ids,
            method=True,
            relation='product.pricelist',
            string='Sale Pricelists',
            type="many2many"),
        'pricelist_purchase':fields.function(
            _pricelist_purchase_ids,
            method=True,
            relation='product.pricelist',
            string='Purchase Pricelists',
            type="many2many"),
    }

product_product()
