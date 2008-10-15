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
        'move_id': fields.many2one('stock.move', 'Move',required=True,domain="[('product_id','=',product_id)]"),#,('location_dest_id','=',location_id),('prodlot_id','=',prodlot_id)
        'guarantee_limit': fields.date('Guarantee limit'),
        'operations' : fields.one2many('repair.operation', 'repair_id', 'Operation Lines', readonly=True, states={'draft':[('readonly',False)]}),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist'),
        'partner_invoice_id':fields.many2one('res.partner.address', 'Invoice to', readonly=True, states={'draft':[('readonly',False)]}, domain="[('partner_id','=',partner_id)]"),
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
    
    def onchange_product_id(self, cr, uid, ids, prod_id=False, move_id=False ):
        if not prod_id:
            return  {'value':{'prodlot_id': False , 'move_id': False, 'location_id' :  False}}
        if move_id:
            move =  self.pool.get('stock.move').browse(cr, uid, move_id)
            product = self.pool.get('product.product').browse(cr, uid, [prod_id])[0]
            date = move.date_planned#time.strftime('%Y-%m-%d')
            limit = mx.DateTime.strptime(date, '%Y-%m-%d %H:%M:%S') + RelativeDateTime(months=product.warranty, days=-1)
            result = {
                'guarantee_limit': limit.strftime('%Y-%m-%d'),
            }
            return { 'value' : result }
        return {}
    
    def onchange_partner_id(self, cr, uid, ids, part):
        if not part:
            return {'value':{'address_id': False , 'pricelist_id': False ,'partner_invoice_id' : False }}
        addr = self.pool.get('res.partner').address_get(cr, uid, [part],  ['delivery','invoice','default'])
        pricelist = self.pool.get('res.partner').property_get(cr, uid,
                        part,property_pref=['property_product_pricelist']).get('property_product_pricelist',False)
        return {'value':{'address_id': addr['delivery'], 'partner_invoice_id' :  addr['invoice'] ,  'pricelist_id': pricelist}}

    
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
        
    def action_cancel_draft(self, cr, uid, ids, *args):
        if not len(ids):
            return False
        self.write(cr, uid, ids, {'state':'draft'})
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_create(uid, 'mrp.repair', id, cr)
        return True

mrp_repair()


class repair_operation(osv.osv):
     _inherit = 'stock.move'
     _name = 'repair.operation'
     _description = 'Repair Operations'
     
     def _get_price(self, cr, uid, ids, name, arg, context={}):
        res = {}
        for val in self.browse(cr, uid, ids):
            current_date = time.strftime('%Y-%m-%d')
            if current_date < val.repair_id.guarantee_limit:
                res[val.id] = 0.0
            if current_date >= val.repair_id.guarantee_limit:
                price = 0.0
                pricelist = val.repair_id.pricelist_id.id
                if pricelist:
                    price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist], val.product_id.id , 1.0, val.repair_id.partner_id.id)[pricelist]
                if price is False:
                     warning={
                        'title':'No valid pricelist line found !',
                        'message':
                            "Couldn't find a pricelist line matching this product and quantity.\n"
                            "You have to change either the product, the quantity or the pricelist."
                        }
                else:
                    res[val.id] = price
        return res
    
    
     _columns = {
        'repair_id': fields.many2one('mrp.repair', 'Repair Order Ref', required=True, ondelete='cascade', select=True),
        'type': fields.selection([('add','Add'),('remove','Remove')],'Type'),
        'invoice': fields.boolean('Invoice'),
        'price_unit': fields.function(_get_price,  method=True, store= True, type='float', string='Price'),
    }
     
     
     def product_id_change(self, cr, uid, ids, pricelist, product, uom=False, product_qty = 0,partner_id=False ):
        if not product:
            return {'value': {'product_qty' : 0.0, 'product_uom': False},'domain': {'product_uom': []}}
        product_obj =  self.pool.get('product.product').browse(cr, uid, product)
        result = {}
        warning = {}
        if not uom:
            result['product_uom'] = product_obj.uom_id.id
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],}
        
        if not pricelist:
            warning={
                'title':'No Pricelist !',
                'message':
                    'You have to select a pricelist in the Repair form !\n'
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
     
     
     def onchange_operation_type(self, cr, uid, ids, type ):
        if not type:
            return {'value':{'location_id': False , 'location_dest_id' :  False}}
        stock_id = self.pool.get('stock.location').search(cr, uid, [('name','=','Stock')])[0]
        produc_id = self.pool.get('stock.location').search(cr, uid, [('name','=','Default Production')])[0]
        if type == 'add':
            return {'value':{'location_id': stock_id , 'location_dest_id' : produc_id}}
        if type == 'remove':
            return {'value':{'location_id': produc_id , 'location_dest_id' : stock_id}}
        
     _defaults = {
                 'name' : lambda *a: 'Repair Operation',
                 }
repair_operation()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
