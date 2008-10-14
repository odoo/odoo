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

import time
from osv import fields,osv
import netsvc
import mx.DateTime
from mx.DateTime import RelativeDateTime, now, DateTime, localtime

class mrp_repair(osv.osv):
    _name = 'mrp.repair'
    
    _columns = {
        'product_id': fields.many2one('product.product', string='Product to Repair', required=True ,domain=[('sale_ok','=',True)]),
        'partner_id' : fields.many2one('res.partner', 'Partner', select=True),
        'address_id': fields.many2one('res.partner.address', 'Delivery Address', domain="[('partner_id','=',partner_id)]"),
        'prodlot_id': fields.many2one('stock.production.lot', 'Lot Number', select=True, domain="[('product_id','=',product_id)]"),
        'state': fields.selection([
            ('draft','Quotation'),
            ('confirmed','Confirmed'),
            ('2binvoiced','To be Invoiced'),
            ('done','Done'),
            ('cancel','Cancel')
            ], 'State', readonly=True, help="Gives the state of the Repairs Order"),
        'location_id': fields.many2one('stock.location', 'Current Location', required=True, select=True),
        'location_dest_id': fields.many2one('stock.location', 'Delivery Location'),
        'move_id': fields.many2one('stock.move', 'Move',required=True,domain="[('product_id','=',product_id),('location_dest_id','=',location_id)]"),#,('prodlot_id','=',prodlot_id)
        'guarantee_limit': fields.date('Guarantee limit'),
        'operations' : fields.one2many('repair.operation', 'repair_id', 'Operation Lines', readonly=True, states={'draft':[('readonly',False)]}),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist'),
        'partner_invoice_id':fields.many2one('res.partner.address', 'Invoice to', readonly=True, states={'draft':[('readonly',False)]}),
        'invoice_method':fields.selection([
            ("none","No Invoice"),
            ("b4repair","Before Repair"),
            ("after_repair","After Repair")
           ], "Invoice Method", 
            select=True),
        'invoice_id': fields.many2one('account.invoice', 'Invoice', readonly=True),
#        'fees_lines' : fields.one2many('sale.order.line', 'order_id', 'Fees Lines', readonly=True, states={'draft':[('readonly',False)]}),
        'internal_notes' : fields.text('Internal Notes'),
        'quotation_notes' : fields.text('Quotation Notes'),
    }
    
    _defaults = {
        'state': lambda *a: 'draft',
    }
    
    def onchange_product_id(self, cr, uid, ids, prod_id=False):
        if not prod_id:
            return  {'value':{'prodlot_id': False , 'move_id': False, 'location_id' :  False}}
        product = self.pool.get('product.product').browse(cr, uid, [prod_id])[0]
        current_date = time.strftime('%Y-%m-%d')
        limit = mx.DateTime.strptime(current_date, '%Y-%m-%d') + RelativeDateTime(months=product.warranty, days=-1)
        result = {
            'guarantee_limit': limit.strftime('%Y-%m-%d'),
        }
        return { 'value' : result }
    
    def onchange_partner_id(self, cr, uid, ids, part):
        if not part:
            return {'value':{'address_id': False , 'pricelist_id': False }}
        addr = self.pool.get('res.partner').address_get(cr, uid, [part])
        pricelist = self.pool.get('res.partner').property_get(cr, uid,
                        part,property_pref=['property_product_pricelist']).get('property_product_pricelist',False)
        return {'value':{'address_id': addr['default'],  'pricelist_id': pricelist}}

    
    def onchange_lot_id(self, cr, uid, ids, lot ):
        if not lot:
            return {'value':{'location_id': False , 'move_id' :  False}}
        lot_info = self.pool.get('stock.production.lot').browse(cr, uid, [lot])[0]
        move_id = self.pool.get('stock.move').search(cr, uid,[('prodlot_id','=',lot)] )
        if move_id: 
            move = self.pool.get('stock.move').browse(cr, uid, move_id )[0]
            return {'value':{'location_id': move.location_dest_id.id ,  'move_id': move.id }}
        else:
            return {'value':{'location_id': False , 'move_id' :  False}}

mrp_repair()


class repair_operation(osv.osv):
     _name = 'repair.operation'
     _description = 'Repair Operation'
     _columns = {
        'repair_id': fields.many2one('mrp.repair', 'Repair Order Ref', required=True, ondelete='cascade', select=True),
        'name': fields.selection([('add','Add'),('remove','Remove')],'Type'),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok','=',True)]),
        'invoice': fields.boolean('Invoice'),
        'price_unit': fields.float('Price'),
        'product_qty': fields.float('Quantity', digits=(16,2)),
        'product_uom': fields.many2one('product.uom', 'UoM'),
         'location_id': fields.many2one('stock.location', 'Source Location', select=True),
        'location_dest_id': fields.many2one('stock.location', 'Dest. Location', select=True),
        'prodlot_id': fields.many2one('stock.production.lot', 'Lot Nb.', select=True),
    }
     
     
     def product_id_change(self, cr, uid, ids, pricelist, product, uom=False, product_qty = 0,partner_id=False ):
        if not product:
            return {'value': {'product_qty' : 0.0, 'product_uom': False},'domain': {'product_uom': []}}

        product_obj =  self.pool.get('product.product').browse(cr, uid, product)
        result = {}
        if not uom:
            result['product_uom'] = product_obj.uom_id.id
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],}
            
        if not pricelist:
            warning={
                'title':'No Pricelist !',
                'message':
                    'You have to select a pricelist in the sale form !\n'
                    'Please set one before choosing a product.'
                }
        else:
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                    product, product_qty or 1.0, partner_id, {
                        'uom': uom,
                        })[pricelist]
            if price is False:
                 warning={
                    'title':'No valid pricelist line found !',
                    'message':
                        "Couldn't find a pricelist line matching this product and quantity.\n"
                        "You have to change either the product, the quantity or the pricelist."
                    }
            else:
                result.update({'price_unit': price})
                
        return {'value': result , 'domain' :domain, 'warning':warning}
    
repair_operation()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
