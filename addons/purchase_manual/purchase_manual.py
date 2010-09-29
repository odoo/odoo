# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

from osv import fields
from osv import osv
import netsvc

class purchase_order_line(osv.osv):
    _inherit='purchase.order.line'
    _columns = {
        'state': fields.selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('cancel', 'Cancelled')], 'Status', required=True, readonly=True),
        'invoice_lines': fields.many2many('account.invoice.line', 'purchase_order_line_invoice_rel', 'order_line_id', 'invoice_id', 'Invoice Lines', readonly=True),
        'invoiced': fields.boolean('Invoiced', readonly=True),
        'partner_id': fields.related('order_id','partner_id',string='Partner',readonly=True,type="many2one", relation="res.partner"),
        'date_order': fields.related('order_id','date_order',string='Order Date',readonly=True,type="date")
    }
    _defaults = {
        'state': lambda *args: 'draft',
        'invoiced': lambda *a: 0,

    }
    def copy_data(self, cr, uid, id, default=None, context={}):
        print 'copy called'
        if not default:
            default = {}
        default.update({
            'state':'draft',
            'invoiced':0,
            'invoice_lines':[],
        })
        return super(purchase_order_line, self).copy_data(cr, uid, id, default, context)
 
    def action_confirm(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state': 'confirmed'}, context)
        return True
purchase_order_line()

class purchase_order(osv.osv):
    _inherit='purchase.order'
    def action_invoice_create(self, cr, uid, ids, context={}):
        res = super(purchase_order, self).action_invoice_create(cr, uid, ids, context)
        for po in self.browse(cr, uid, ids, context):
            todo = []
            for line in po.order_line:
                todo.append(line.id)
            self.pool.get('purchase.order.line').write(cr, uid, todo, {'invoiced':True}, context)
        return res

    def wkf_confirm_order(self, cr, uid, ids, context={}):
        res = super(purchase_order, self).wkf_confirm_order(cr, uid, ids, context)
        todo = []
        for po in self.browse(cr, uid, ids, context):
            for line in po.order_line:
                if line.state=='draft':
                    todo.append(line.id)
        self.pool.get('purchase.order.line').action_confirm(cr, uid, todo, context)
        return res
    _columns = {
        'name': fields.char('Order SDER', size=64, required=True, select=True,
readonly=True)
        
                }
purchase_order()
