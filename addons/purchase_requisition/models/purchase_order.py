# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp


class purchase_order(osv.osv):
    _inherit = "purchase.order"

    _columns = {
        'requisition_id': fields.many2one('purchase.requisition', 'Call for Tenders', copy=False),
    }

    def button_confirm(self, cr, uid, ids, context=None):
        res = super(purchase_order, self).button_confirm(cr, uid, ids, context=context)
        proc_obj = self.pool.get('procurement.order')
        for po in self.browse(cr, uid, ids, context=context):
            if po.requisition_id and (po.requisition_id.exclusive == 'exclusive'):
                for order in po.requisition_id.purchase_ids:
                    if order.id != po.id:
                        proc_ids = proc_obj.search(cr, uid, [('purchase_id', '=', order.id)])
                        if proc_ids and po.state == 'confirmed':
                            proc_obj.write(cr, uid, proc_ids, {'purchase_id': po.id})
                        order.button_cancel()
                    po.requisition_id.tender_done(context=context)
            for element in po.order_line:
                if not element.quantity_tendered:
                    element.write({'quantity_tendered': element.product_qty})
        return res


class purchase_order_line(osv.osv):
    _inherit = 'purchase.order.line'

    _columns = {
        'quantity_tendered': fields.float('Quantity Tendered', digits_compute=dp.get_precision('Product Unit of Measure'), help="Technical field for not loosing the initial information about the quantity proposed in the tender", oldname='quantity_bid'),
    }

    def generate_po(self, cr, uid, tender_id, context=None):
        #call generate_po from tender with active_id. Called from js widget
        return self.pool.get('purchase.requisition').generate_po(cr, uid, [tender_id], context=context)

    def button_confirm(self, cr, uid, ids, context=None):
        for element in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, element.id, {'quantity_tendered': element.product_qty}, context=context)
        return True

    def button_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'quantity_tendered': 0}, context=context)
        return True
