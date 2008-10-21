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
    _description = 'Repairs Order'
    _columns = {
        'name' : fields.char('Name',size=24),
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
        'operations' : fields.one2many('mrp.repair.lines', 'repair_id', 'Operation Lines', readonly=True, states={'draft':[('readonly',False)]}),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist'),
        'partner_invoice_id':fields.many2one('res.partner.address', 'Invoice to', readonly=True, states={'draft':[('readonly',False)]}, domain="[('partner_id','=',partner_id)]"),
        'invoice_method':fields.selection([
            ("none","No Invoice"),
            ("b4repair","Before Repair"),
            ("after_repair","After Repair")
           ], "Invoice Method", 
            select=True),
        'invoice_id': fields.many2one('account.invoice', 'Invoice', readonly=True),
        'fees_lines' : fields.one2many('mrp.repair.fee', 'repair_id', 'Fees Lines', readonly=True, states={'draft':[('readonly',False)]}),
        'internal_notes' : fields.text('Internal Notes'),
        'quotation_notes' : fields.text('Quotation Notes'),
    }
    
    _defaults = {
        'state': lambda *a: 'draft',
        'invoice_method': lambda *a: 'none',
        'pricelist_id': lambda self, cr, uid,context : self.pool.get('product.pricelist').search(cr,uid,[('type','=','sale')])[0]
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
            return {'value':{'address_id': False ,'partner_invoice_id' : False }}
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
#            self.onchange_product_id(cr, uid, ids, prod_id, move_id)
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

    def action_wait(self, cr, uid, ids, *args):
        for o in self.browse(cr, uid, ids):
            if (o.invoice_method == 'none'):
                self.write(cr, uid, [o.id], {'state': 'confirmed'})
            elif (o.invoice_method == 'b4repair'):
                self.write(cr, uid, [o.id], {'state': '2binvoiced'})
            elif (o.invoice_method == 'after_repair'):
                self.write(cr, uid, [o.id], {'state': 'confirmed'})
        self.pool.get('mrp.repair.lines').write(cr, uid, ids, {'state':'confirmed'})
        return True
    
    def action_invoice_create(self, cr, uid, ids, grouped=False, states=['confirmed','done']):
        res = False
        invoices = {}
        invoice_ids = []

        for o in self.browse(cr,uid,ids):
            lines = []
            for line in o.operations:
                if (line.state in states) and not line.invoiced:
                    lines.append(line.id)
#            created_lines = self.pool.get('sale.order.line').invoice_line_create(cr, uid, lines)
#            if created_lines:
#                invoices.setdefault(o.partner_id.id, []).append((o, created_lines))

        picking_obj=self.pool.get('stock.picking')
        for val in invoices.values():
            if grouped:
                res = self._make_invoice(cr, uid, val[0][0], reduce(lambda x,y: x + y, [l for o,l in val], []))
                for o,l in val:
                    self.write(cr, uid, [o.id], {'state' : 'progress'})
                    if o.order_policy=='picking':
                        picking_obj.write(cr,uid,map(lambda x:x.id,o.picking_ids),{'invoice_state':'invoiced'})
                    cr.execute('insert into sale_order_invoice_rel (order_id,invoice_id) values (%d,%d)', (o.id, res))
            else:
                for order, il in val:
                    res = self._make_invoice(cr, uid, order, il)
                    invoice_ids.append(res)
                    self.write(cr, uid, [order.id], {'state' : 'progress'})
                    if order.order_policy=='picking':
                        picking_obj.write(cr,uid,map(lambda x:x.id,order.picking_ids),{'invoice_state':'invoiced'})
                    cr.execute('insert into sale_order_invoice_rel (order_id,invoice_id) values (%d,%d)', (order.id, res))
        return res


    def action_ship_create(self, cr, uid, ids, *args):
        picking_id=False
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        for repair in self.browse(cr, uid, ids, context={}):
            if repair.location_dest_id:
                output_id = repair.location_dest_id.id
                for line in repair.operations:
                    proc_id=False
                    date_planned = time.strftime('%Y-%m-%d %H:%M:%S')
                    if line.product_id and line.product_id.product_tmpl_id.type in ('product', 'consu'):
                        location_id = line.location_id.id
                        if not picking_id:
                            picking_id = self.pool.get('stock.picking').create(cr, uid, {
                                'origin': repair.product_id.code, # + (repair.partner_id and  repair.partner_id.name) or ' ',
                                'type': 'out',
                                'state': 'auto',
                                'move_type': 'one',
                                'address_id': repair.address_id.id,
                                'note': repair.internal_notes,
                                'invoice_state': 'none',
                            })
#                            operation = self.pool.get('stock.move')
#                            operation.write(cr, uid, line.id,{'picking_id' : picking_id} )
                        vals = {
                            'name': line.product_id.name[:64],
                            'picking_id': picking_id,
                            'product_id': line.product_id.id,
                            'date_planned': date_planned,
                            'product_qty': line.product_uom_qty,
                            'product_uom': line.product_uom.id,
                            'product_uos_qty': line.product_uos_qty,
                            'product_uos': (line.product_uos and line.product_uos.id)\
                                    or line.product_uom.id,
                            'product_packaging' : line.product_packaging.id,
                            'address_id': repair.address_id.id,
                            'location_id': location_id,
                            'location_dest_id': output_id,
                            'tracking_id': False,
                            'state': 'draft',
                            'note': line.notes,
                        }
                        move_id = self.pool.get('stock.move').create(cr, uid, vals)
                        proc_id = self.pool.get('mrp.procurement').create(cr, uid, {
                            'name': repair.name or 'Repair',
                            'origin': repair.name,
                            'date_planned': date_planned,
                            'product_id': line.product_id.id,
                            'product_qty': line.product_uom_qty,
                            'product_uom': line.product_uom.id,
                            'location_id': repair.location_id.id,
                            'procure_method': 'make_to_stock' ,# NEEDS TO BE CHANGED
                            'move_id': line.id,
                        })
                        wf_service = netsvc.LocalService("workflow")
                        wf_service.trg_validate(uid, 'mrp.procurement', proc_id, 'button_confirm', cr)
                        self.pool.get('mrp.repair.lines').write(cr, uid, [line.id], {'procurement_id': proc_id})
                    elif line.product_id and line.product_id.product_tmpl_id.type=='service':
                        proc_id = self.pool.get('mrp.procurement').create(cr, uid, {
                            'name': line.name or 'Repair',
                            'origin': repair.name,
                            'date_planned': date_planned,
                            'product_id': line.product_id.id,
                            'product_qty': line.product_uom_qty,
                            'product_uom': line.product_uom.id,
                            'location_id': repair.location_id.id,
                            'procure_method': 'make_to_stock' ,# NEEDS TO BE CHANGED
                        })
                        wf_service = netsvc.LocalService("workflow")
                        wf_service.trg_validate(uid, 'mrp.procurement', proc_id, 'button_confirm', cr)
                        self.pool.get('mrp.repair.lines').write(cr, uid, [line.id], {'procurement_id': proc_id})
                    else:
                        #
                        # No procurement because no product in the sale.order.line.
                        #
                        pass
    
                val = {}
                if picking_id:
                    wf_service = netsvc.LocalService("workflow")
                    wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
                self.write(cr, uid, [repair.id], val)
                
        return True

    def procurement_lines_get(self, cr, uid, ids, *args):
        res = []
        for order in self.browse(cr, uid, ids, context={}):
            for line in order.operations:
                if line.procurement_id:
                    res.append(line.procurement_id.id)
        return res
    
    def test_state(self, cr, uid, ids, mode, *args):
        assert mode in ('finished', 'canceled'), _("invalid mode for test_state")
        finished = True
        canceled = False
        write_done_ids = []
        write_cancel_ids = []
        for order in self.browse(cr, uid, ids, context={}):
            for line in order.operations:
                if line.procurement_id and (line.procurement_id.state != 'done') and (line.state!='done'):
                    finished = False
                if line.procurement_id and line.procurement_id.state == 'cancel':
                    canceled = True
                # if a line is finished (ie its procuremnt is done or it has not procuremernt and it
                # is not already marked as done, mark it as being so...
                if ((not line.procurement_id) or line.procurement_id.state == 'done') and line.state != 'done':
                    write_done_ids.append(line.id)
                # ... same for canceled lines
                if line.procurement_id and line.procurement_id.state == 'cancel' and line.state != 'cancel':
                    write_cancel_ids.append(line.id)
        if write_done_ids:
            self.pool.get('mrp.repair.lines').write(cr, uid, write_done_ids, {'state': 'done'})
        if write_cancel_ids:
            self.pool.get('mrp.repair.liness').write(cr, uid, write_cancel_ids, {'state': 'cancel'})

        if mode=='finished':
            return finished
        elif mode=='canceled':
            return canceled
        
    def action_ship_end(self, cr, uid, ids, context={}):
        for order in self.browse(cr, uid, ids):
            val = {}
            if (order.invoice_method=='after_repair'):
                val['state'] = '2binvoiced'
            else:
                val['state'] = 'confirmed'
            self.write(cr, uid, [order.id], val)
        return True
mrp_repair()


class repair_operation(osv.osv):
    _name = 'mrp.repair.lines'
    _description = 'Repair Operations'
     
    def _get_price(self, cr, uid, ids, name, arg, context={}):
        res = {}
        for val in self.browse(cr, uid, ids):
            if val.repair_id:
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
    
    def _amount_line_net(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for line in self.browse(cr, uid, ids):
            res[line.id] = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        return res

    def _amount_line(self, cr, uid, ids, field_name, arg, context):
        res = {}
        cur_obj=self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids):
            res[line.id] = line.price_unit * line.product_uom_qty * (1 - (line.discount or 0.0) / 100.0)
            cur = line.repair_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
        return res
    _columns = {
                'name' : fields.char('Name',size=24),
                'repair_id': fields.many2one('mrp.repair', 'Repair Order Ref',ondelete='cascade', select=True),
                'type': fields.selection([('add','Add'),('remove','Remove')],'Type'),
                'invoice': fields.boolean('Invoice'),
                'delay': fields.float('Delivery Delay', required=True),
                'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok','=',True)],  required=True),
                'invoiced': fields.boolean('Invoiced'),
                'procurement_id': fields.many2one('mrp.procurement', 'Procurement'),
                'price_unit': fields.function(_get_price,  method=True, store= True, type='float', string='Price'),
                'price_net': fields.function(_amount_line_net, method=True, string='Net Price'),
                'price_subtotal': fields.function(_amount_line, method=True, string='Subtotal'),
                'tax_id': fields.many2many('account.tax', 'sale_order_tax', 'order_line_id', 'tax_id', 'Taxes'),
                'property_ids': fields.many2many('mrp.property', 'sale_order_line_property_rel', 'order_id', 'property_id', 'Properties'),
                'address_allotment_id' : fields.many2one('res.partner.address', 'Allotment Partner'),
                'product_uom_qty': fields.float('Quantity (UoM)', digits=(16,2), required=True),
                'product_uom': fields.many2one('product.uom', 'Product UoM', required=True),
                'product_uos_qty': fields.float('Quantity (UOS)'),
                'product_uos': fields.many2one('product.uom', 'Product UOS'),
                'product_packaging': fields.many2one('product.packaging', 'Packaging'),
                'move_ids': fields.one2many('stock.move', 'sale_line_id', 'Inventory Moves', readonly=True),
                'discount': fields.float('Discount (%)', digits=(16,2)),
                'notes': fields.text('Notes'),
                'th_weight' : fields.float('Weight'),
                'location_id': fields.many2one('stock.location', 'Source Location', required=True, select=True),
                'location_dest_id': fields.many2one('stock.location', 'Dest. Location', required=True, select=True),
                'state': fields.selection([('draft','Draft'),('confirmed','Confirmed'),('done','Done'),('cancel','Canceled')], 'Status', required=True, readonly=True),
    }
     
     
    def product_id_change(self, cr, uid, ids, pricelist, product, uom=False, product_uom_qty = 0,partner_id=False ):
        if not product:
            return {'value': {'product_uom_qty' : 0.0, 'product_uom': False},'domain': {'product_uom': []}}
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
                    product, product_uom_qty or 1.0, partner_id, {
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
                 'state': lambda *a: 'draft',
                 }
    
repair_operation()

class mrp_repair_fee(osv.osv):
    _name = 'mrp.repair.fee'
    _description = 'Repair Fees line'
    _columns = {
        'repair_id': fields.many2one('mrp.repair', 'Repair Order Ref', required=True, ondelete='cascade', select=True),
        'name': fields.char('Description', size=8, required=True, select=True),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_uom_qty': fields.float('Quantity', digits=(16,2), required=True),
        'price_unit': fields.float('Unit Price', required=True),
        'product_uom': fields.many2one('product.uom', 'Product UoM', required=True),
    }
    
    def product_id_change(self, cr, uid, ids, product, uom=False):
        if not product:
            return {'value': {'product_uom_qty' : 0.0, 'product_uom': False},'domain': {'product_uom': []}}
        
        product_obj =  self.pool.get('product.product').browse(cr, uid, product)
        result = {}
        if not uom:
            result['product_uom'] = product_obj.uom_id.id
        domain = {'product_uom':
                    [('category_id', '=', product_obj.uom_id.category_id.id)],}
        return {'value': result ,'domain': domain}
    
mrp_repair_fee()


class stock_move(osv.osv):
    _inherit = "stock.move"
    _columns = {
                'state': fields.selection([('draft','Draft'),('waiting','Waiting'),('confirmed','Confirmed'),('assigned','Assigned'),('done','Done'),('cancel','cancel'),('in_repair','In Repair')], 'Status',),# readonly=True, select=True),
                'repair_ids' : fields.one2many('mrp.repair', 'move_id', 'Repairs'),
            }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
