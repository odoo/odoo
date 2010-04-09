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

from osv import fields,osv
from osv import orm
import netsvc
import time

class purchase_requisition(osv.osv):
    _name = "purchase.requisition"
    _description="Purchase requisition"
    _columns = {
        'name': fields.char('Requisition Reference', size=32,required=True),
        'date_start': fields.datetime('Date Start'),
        'date_end': fields.datetime('Date End'),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'exclusive': fields.boolean('Exclusive', help="If the requisition is exclusive, it will cancel all purchase orders when you confirm one of them"),
        'description': fields.text('Description'),
        'purchase_ids' : fields.one2many('purchase.order','requisition_id','Purchase Orders'),
        'line_ids' : fields.one2many('purchase.requisition.line','requisition_id','Products to Purchase'),
        'state': fields.selection([('draft','Draft'),('open','Open'),('close','Close')], 'State', required=True)
    }
    _defaults = {
        'date_start': lambda *args: time.strftime('%Y-%m-%d %H:%M:%S'),
        'state': lambda *args: 'open',
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'purchase.order.requisition'),
    }
purchase_requisition()

class purchase_requisition_line(osv.osv):
    _name = "purchase.requisition.line"
    _description="Purchase Requisition Line"
    _rec_name = 'product_id'
    _columns = {
        'product_id': fields.many2one('product.product', 'Product'),
        'product_uom_id': fields.many2one('product.uom', 'Product UoM'),
        'product_qty': fields.float('Date End', digits=(16,2)),
        'requisition_id' : fields.many2one('purchase.requisition','Purchase Requisition', ondelete='cascade')
    }
purchase_requisition_line()

class purchase_order(osv.osv):
    _inherit = "purchase.order"
    _description = "purchase order"
    _columns = {
        'requisition_id' : fields.many2one('purchase.requisition','Purchase Requisition')
    }
    def wkf_confirm_order(self, cr, uid, ids, context={}):
        res = super(purchase_order, self).wkf_confirm_order(cr, uid, ids, context)
        for po in self.browse(cr, uid, ids, context):
            if po.requisition_id and po.requisition_id.exclusive:
                for order in po.requisition_id.purchase_ids:
                    if order.id<>po.id:
                        wf_service = netsvc.LocalService("workflow")
                        wf_service.trg_validate(uid, 'purchase.order', order.id, 'purchase_cancel', cr)
                    self.pool.get('purchase.requisition').write(cr, uid, [po.requisition_id.id], {'state':'close'})
        return res
purchase_order()


class product_product(osv.osv):
    _inherit = 'product.product'
    _columns = {
        'purchase_requisition': fields.boolean('Purchase Requisition', help="Check this box so that requisitions generates purchase requisitions instead of directly requests for quotations.")
    }
    _defaults = {
        'purchase_requisition': lambda *args: False
    }
product_product()


class mrp_procurement(osv.osv):
    _inherit = 'mrp.procurement'
    def make_po(self, cr, uid, ids, context={}):
        res = super(mrp_procurement, self).make_po(cr, uid, ids, context)
        for proc_id,po_id in res.items():
            procurement = self.browse(cr, uid, proc_id)
            if procurement.product_id.purchase_requisition:
                self.pool.get('purchase.requisition').create(cr, uid, {
                    'name': procurement.name,
                    'lines_ids': [(0,0,{
                        'product_id': procurement.product_id.id,
                        'product_uom_id': procurement.product_uom.id,
                        'product_qty': procurement.product_qty

                    })],
                    'purchase_ids': [(6,0,[po_id])]
                })
mrp_procurement()
