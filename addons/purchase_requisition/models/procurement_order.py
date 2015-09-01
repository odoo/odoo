# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _


class procurement_order(osv.osv):
    _inherit = 'procurement.order'
    _columns = {
        'requisition_id': fields.many2one('purchase.requisition', 'Latest Requisition')
    }

    def make_po(self, cr, uid, ids, context=None):
        requisition_obj = self.pool.get('purchase.requisition')
        warehouse_obj = self.pool.get('stock.warehouse')
        req_ids = []
        res = []
        for procurement in self.browse(cr, uid, ids, context=context):
            if procurement.product_id.purchase_requisition == 'tenders':
                warehouse_id = warehouse_obj.search(cr, uid, [('company_id', '=', procurement.company_id.id)], context=context)
                requisition_id = requisition_obj.create(cr, uid, {
                    'origin': procurement.origin,
                    'date_end': procurement.date_planned,
                    'warehouse_id': warehouse_id and warehouse_id[0] or False,
                    'company_id': procurement.company_id.id,
                    'procurement_id': procurement.id,
                    'picking_type_id': procurement.rule_id.picking_type_id.id,
                    'line_ids': [(0, 0, {
                        'product_id': procurement.product_id.id,
                        'product_uom_id': procurement.product_uom.id,
                        'product_qty': procurement.product_qty
                    })],
                })
                self.message_post(cr, uid, [procurement.id], body=_("Purchase Requisition created"), context=context)
                procurement.write({'requisition_id': requisition_id})
                req_ids += [procurement.id]
        set_others = set(ids) - set(req_ids)
        if set_others:
            res += super(procurement_order, self).make_po(cr, uid, list(set_others), context=context)
        return res
