# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

class purchase_requisition_partner(osv.osv_memory):
    _name = "purchase.requisition.partner"
    _description = "Purchase Requisition Partner"
    _columns = {
        'partner_ids': fields.many2many('res.partner', 'purchase_requisition_supplier_rel', 'requisition_id', 'partner_id', string='Vendors', required=True, domain=[('supplier', '=', True)])
    }

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        res = super(purchase_requisition_partner, self).view_init(cr, uid, fields_list, context=context)
        record_id = context and context.get('active_id', False) or False
        tender = self.pool.get('purchase.requisition').browse(cr, uid, record_id, context=context)
        if not tender.line_ids:
            raise UserError(_('Define product(s) you want to include in the call for tenders.'))
        return res

    def create_order(self, cr, uid, ids, context=None):
        active_ids = context and context.get('active_ids', [])
        purchase_requisition = self.pool.get('purchase.requisition')
        for wizard in self.browse(cr, uid, ids, context=context):
            for partner_id in wizard.partner_ids:
                purchase_requisition.make_purchase_order(cr, uid, active_ids, partner_id.id, context=context)
        return {'type': 'ir.actions.act_window_close'}
