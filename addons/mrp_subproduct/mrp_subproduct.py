# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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

from osv import fields
from osv import osv

class mrp_subproduct(osv.osv):
    _name = 'mrp.subproduct'
    _description = 'Mrp Sub Product'
    _columns={
              'product_id': fields.many2one('product.product', 'Product', required=True),
              'product_qty': fields.float('Product Qty', required=True),
              'product_uom': fields.many2one('product.uom', 'Product UOM', required=True),
              'bom_id': fields.many2one('mrp.bom', 'BoM'),
              }
    def onchange_product_id(self, cr, uid, ids, product_id,context={}):
         if product_id:
            prod=self.pool.get('product.product').browse(cr,uid,product_id)
            v = {'product_uom':prod.uom_id.id}
            return {'value': v}
         return {}

mrp_subproduct()

class mrp_bom(osv.osv):
    _name = 'mrp.bom'
    _description = 'Bill of Material'
    _inherit='mrp.bom'
    _columns={
              'sub_products':fields.one2many('mrp.subproduct', 'bom_id', 'sub_products'),
              }


mrp_bom()

class mrp_production(osv.osv):
    _name = 'mrp.production'
    _description = 'Production'
    _inherit= 'mrp.production'   

    def action_confirm(self, cr, uid, ids):
         picking_id=super(mrp_production,self).action_confirm(cr, uid, ids)
         for production in self.browse(cr, uid, ids):
             source = production.product_id.product_tmpl_id.property_stock_production.id
             for sub_product in production.bom_id.sub_products:               

                 data = {
                    'name':'PROD:'+production.name,
                    'date_planned': production.date_planned,
                    'product_id': sub_product.product_id.id,
                    'product_qty': sub_product.product_qty,
                    'product_uom': sub_product.product_uom.id,
                    'product_uos_qty': production.product_uos and production.product_uos_qty or False,
                    'product_uos': production.product_uos and production.product_uos.id or False,
                    'location_id': source,
                    'location_dest_id': production.location_dest_id.id,
                    'move_dest_id': production.move_prod_id.id,
                    'state': 'waiting',
                    'production_id':production.id
                 }
                 sub_prod_ids=self.pool.get('stock.move').create(cr, uid,data)
         return picking_id

mrp_production()
