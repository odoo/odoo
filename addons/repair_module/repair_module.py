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
        'move_id': fields.many2one('stock.move', 'Move',required=True,domain="[('product_id','=',product_id)]"),#,('prodlot_id','=',prodlot_id)
        'limit': fields.date('Guarantee limit',  readonly=True),
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
        'fees_lines' : fields.one2many('sale.order.line', 'order_id', 'Fees Lines', readonly=True, states={'draft':[('readonly',False)]}),
        'internal_notes' : fields.text('Internal Notes'),
        'quotation_notes' : fields.text('Quotation Notes'),
    }
    
    _defaults = {
        'state': lambda *a: 'draft',
    }
    
mrp_repair()


class repair_operation(osv.osv):
     _name = 'repair.operation'
     _description = 'Repair Operation'
     _columns = {
        'repair_id': fields.many2one('mrp.repair', 'Repair Order Ref', required=True, ondelete='cascade', select=True),
        'name': fields.selection([('add','Add'),('remove','Remove')],'Type',  required=True),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok','=',True)]),
        'invoice': fields.boolean('Invoice', readonly=True),
        'price_unit': fields.float('Price', required=True),
        'product_qty': fields.float('Quantity', digits=(16,2), required=True),
        'product_uom': fields.many2one('product.uom', 'UoM', required=True),
         'location_id': fields.many2one('stock.location', 'Source Location', select=True),
        'location_dest_id': fields.many2one('stock.location', 'Dest. Location', select=True),
        'prodlot_id': fields.many2one('stock.production.lot', 'Lot Nb.', select=True),
    }

repair_operation()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
