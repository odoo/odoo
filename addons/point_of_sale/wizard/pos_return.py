# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

import netsvc
from osv import osv,fields
from tools.translate import _
import time

class pos_return(osv.osv_memory):
    _name = 'pos.return'
    _description = 'Point of sale return'
    _columns = {
        'pos_moves_ids' : fields.one2many('pos.return.memory', 'pos_moves_id', 'Moves'),
     }

    def default_get(self, cr, uid, fields, context=None):
        """
             To get default values for the object.

             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param fields: List of fields for which we want default values
             @param context: A standard dictionary

             @return: A dictionary which of fields with values.

        """
        res = super(pos_return, self).default_get(cr, uid, fields, context=context)
        order_obj = self.pool.get('pos.order')
        if context is None:
            context={}
        active_ids = context.get('active_ids')
        result=[]
        for order in order_obj.browse(cr, uid, active_ids, context=context):
            for line in order.lines:
                result.append({
                            'product_id' : line.product_id.id, 
                            'quantity' : line.qty, 
                            'line_id':line.id
                        })
            res.update({'pos_moves_ids': result})
        return res

    def  create_returns(self, cr, uid, data, context=None):
        """
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary

             @return: Return the add product form again for adding more product

        """
        if context is None:
            context = {}
        current_rec = self.browse(cr, uid, data, context=context)[0]
        order_obj =self.pool.get('pos.order')
        line_obj = self.pool.get('pos.order.line')
        pos_current = order_obj.browse(cr, uid, context.get('active_id'), context=context)
        for pos_line in pos_current.lines:
            for record in current_rec.pos_moves_ids:
                if pos_line.id == record.line_id:
                    less_qty = record.quantity
                    line_obj.write(cr, uid, pos_line.id, {'qty':pos_line.qty - less_qty}, context=context)
        return {
            'name': _('Add Product'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.add.product',
            'view_id': False,
            'target':'new',
            'views': False,
            'context': context,
            'type': 'ir.actions.act_window',
        }
    def create_returns2(self, cr, uid, ids, context=None):
       
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        order_obj =self.pool.get('pos.order')
        line_obj = self.pool.get('pos.order.line')
        picking_obj = self.pool.get('stock.picking')
        stock_move_obj = self.pool.get('stock.move')
        property_obj= self.pool.get("ir.property")
        uom_obj =self. pool.get('product.uom')
        statementl_obj = self.pool.get('account.bank.statement.line')
        wf_service = netsvc.LocalService("workflow")
        #Todo :Need to clean the code
        if active_id:
            data = self.browse(cr, uid, ids, context=context)[0]
            date_cur = time.strftime('%Y-%m-%d %H:%M:%S')

            for order_id in order_obj.browse(cr, uid, [active_id], context=context):
                source_stock_id = property_obj.get(cr, uid, 'property_stock_customer', 'res.partner', context=context).id
                cr.execute("SELECT s.id FROM stock_location s, stock_warehouse w "
                            "WHERE w.lot_stock_id=s.id AND w.id=%s ", 
                            (order_id.shop_id.warehouse_id.id,))
                res = cr.fetchone()
                location_id = res and res[0] or None
                new_picking = picking_obj.copy(cr, uid, order_id.picking_id.id, {'name':'%s (return)' % order_id.name,
                                                                               'move_lines': [],
                                                                               'state':'draft',
                                                                               'type': 'in',
                                                                               'address_id': order_id.partner_id.id,
                                                                               'date': date_cur })
                new_order = order_obj.copy(cr, uid, order_id.id, {'name': 'Refund %s'%order_id.name,
                                                              'lines':[],
                                                              'statement_ids':[],
                                                              'picking_id':[]})
                account_def = property_obj.get(cr, uid, 'property_account_payable', 'res.partner', context=context)
                amount = 0.0
                for line in order_id.lines:
                    for record in data.pos_moves_ids:
                        if line.id == record.line_id:
                            qty = record.quantity
                            amount += qty * line.price_unit
                            stock_move_obj.create(cr, uid, {
                                'product_qty': qty ,
                                'product_uos_qty': uom_obj._compute_qty(cr, uid, qty ,line.product_id.uom_id.id),
                                'picking_id': new_picking,
                                'product_uom': line.product_id.uom_id.id,
                                'location_id': source_stock_id,
                                'product_id': line.product_id.id,
                                'location_dest_id': location_id,
                                'name': '%s (return)' %order_id.name,
                                'date': date_cur
                            })
                            if qty != 0.0:
                                line_obj.copy(cr, uid, line.id, {'qty': -qty, 'order_id': new_order})
                statementl_obj.create(cr, uid, {
                                                'name': 'Refund %s'%order_id.name,
                                                'statement_id': order_id.statement_ids[0].statement_id.id,
                                                'pos_statement_id': new_order,
                                                'date': time.strftime('%Y-%m-%d'),
                                                'account_id': order_id.partner_id and order_id.partner_id.property_account_payable \
                                                             and order_id.partner_id.property_account_payable.id or account_def.id,
                                                'amount': -amount,
                                                })
                order_obj.write(cr,uid, [active_id,new_order], {'state': 'done'})
                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_confirm', cr)
                picking_obj.force_assign(cr, uid, [new_picking], context)
            act = {
                'domain': "[('id', 'in', ["+str(new_order)+"])]",
                'name': 'Refunded Orders',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'pos.order',
                'auto_refresh':0,
                'res_id':new_order,
                'view_id': False,
                'context':context,
                'type': 'ir.actions.act_window'
            }
        return act

pos_return()

class add_product(osv.osv_memory):
    _inherit = 'pos.add.product'
    def select_product(self, cr, uid, ids, context=None):
        """
             To get the product and quantity and add in order .
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return : Retrun the add product form again for adding more product
        """
        if context is None:
            context = {}

        active_id=context.get('active_id', False)
        data =  self.read(cr, uid, ids)
        data = data and data[0] or False
        if active_id:
            order_obj = self.pool.get('pos.order')
            picking_obj = self.pool.get('stock.picking')
            stock_move_obj = self.pool.get('stock.move')
            property_obj= self.pool.get("ir.property")
            date_cur=time.strftime('%Y-%m-%d')
            uom_obj = self.pool.get('product.uom')
            prod_obj=self.pool.get('product.product')
            wf_service = netsvc.LocalService("workflow")
            order_obj.add_product(cr, uid, active_id, data['product_id'], data['quantity'], context=context)

            for order_id in order_obj.browse(cr, uid, [active_id], context=context):
                prod=data['product_id']
                qty=data['quantity']
                stock_dest_id = property_obj.get(cr, uid, 'property_stock_customer', 'res.partner', context=context).id
                cr.execute("SELECT s.id FROM stock_location s, stock_warehouse w "
                            "WHERE w.lot_stock_id=s.id AND w.id=%s ",
                            (order_id.shop_id.warehouse_id.id,))
                res=cr.fetchone()
                location_id=res and res[0] or None
                prod_id=prod_obj.browse(cr, uid, prod, context=context)
                new_picking=picking_obj.create(cr, uid, {
                                'name':'%s (Added)' %order_id.name,
                                'move_lines':[],
                                'state':'draft',
                                'type':'out',
                                'date':date_cur
                            })
                stock_move_obj.create(cr, uid, {
                                'product_qty': qty,
                                'product_uos_qty': uom_obj._compute_qty(cr, uid, prod_id.uom_id.id, qty, prod_id.uom_id.id),
                                'picking_id':new_picking,
                                'product_uom':prod_id.uom_id.id,
                                'location_id':location_id,
                                'product_id':prod_id.id,
                                'location_dest_id':stock_dest_id,
                                'name':'%s (return)' %order_id.name,
                                'date':date_cur
                            })

                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_confirm', cr)
                picking_obj.force_assign(cr, uid, [new_picking], context)
                order_obj.write(cr,uid,active_id,{'picking_id':new_picking})

        return {
            'name': _('Add Product'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.add.product',
            'view_id': False,
            'target':'new',
            'context':context,
            'views': False,
            'type': 'ir.actions.act_window',
        }

    def close_action(self, cr, uid, ids, context=None):
        if context is None: context = {}
        active_ids=context.get('active_ids', False)
        order_obj = self.pool.get('pos.order')
        lines_obj = self.pool.get('pos.order.line')
        picking_obj = self.pool.get('stock.picking')
        stock_move_obj = self.pool.get('stock.move')
        property_obj= self.pool.get("ir.property")
        invoice_obj=self.pool.get('account.invoice')
        date_cur=time.strftime('%Y-%m-%d %H:%M:%S')
        uom_obj = self.pool.get('product.uom')
        return_boj=self.pool.get('pos.return')
        return_id = return_boj.search(cr,uid,[])
        data = {}
        if return_id:
            data = return_boj.read(cr,uid,return_id,[])[0]

        wf_service = netsvc.LocalService("workflow")
        self_data = self.browse(cr, uid, ids, context=context)[0]
        order_obj.add_product(cr, uid, active_ids[0], self_data.product_id.id, self_data.quantity, context=context)
        
        for order_id in order_obj.browse(cr, uid, active_ids, context=context):
            stock_dest_id = property_obj.get(cr, uid, 'property_stock_customer', 'res.partner', context=context).id
            cr.execute("SELECT s.id FROM stock_location s, stock_warehouse w "
                        " WHERE w.lot_stock_id=s.id AND w.id=%s ",
                        (order_id.shop_id.warehouse_id.id,))
            res=cr.fetchone()
            location_id=res and res[0] or None

            if order_id.invoice_id:
                invoice_obj.refund(cr, uid, [order_id.invoice_id.id], time.strftime('%Y-%m-%d'), False, order_id.name)
            new_picking=picking_obj.create(cr, uid, {
                            'name':'%s (return)' %order_id.name,
                            'move_lines':[], 'state':'draft',
                            'type':'in',
                            'date':date_cur
                        })
            for line in order_id.lines:
                key= 'return%s' % line.id
                if line.id: 
                    if data.has_key(key):
                        qty = data[key]
                        lines_obj.write(cr,uid,[line.id], {
                                'qty':line.qty-(data[key] or 0.0)
                        })
                    else:
                        qty = line.qty
                    stock_move_obj.create(cr, uid, {
                        'product_qty': qty,
                        'product_uos_qty': uom_obj._compute_qty(cr, uid, qty, line.product_id.uom_id.id),
                        'picking_id':new_picking,
                        'product_uom':line.product_id.uom_id.id,
                        'location_id':location_id,
                        'product_id':line.product_id.id,
                        'location_dest_id':stock_dest_id,
                        'name':'%s (return)' % order_id.name,
                        'date':date_cur,
                    })
            wf_service.trg_validate(uid, 'stock.picking',new_picking,'button_confirm', cr)
            picking_obj.force_assign(cr, uid, [new_picking], context)
        obj=order_obj.browse(cr,uid, active_ids[0])
        context.update({'return':'return'})

        if obj.amount_total != obj.amount_paid:
            return {
                'name': _('Make Payment'),
                'context ':context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'pos.make.payment',
                'view_id': False,
                'target': 'new',
                'views': False,
                'type': 'ir.actions.act_window',
            }
        return True

add_product()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
