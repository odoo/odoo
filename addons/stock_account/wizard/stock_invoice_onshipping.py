# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

INVOICE_TYPE_MAP = {
    ('outgoing', 'customer'): ['out_invoice'],
    ('outgoing', 'supplier'): ['in_refund'],
    ('outgoing', 'transit'): ['out_invoice', 'in_refund'],
    ('incoming', 'supplier'): ['in_invoice'],
    ('incoming', 'customer'): ['out_refund'],
    ('incoming', 'transit'): ['in_invoice', 'out_refund'],
}


class stock_invoice_onshipping(osv.osv_memory):
    def _get_journal(self, cr, uid, context=None):
        journal_obj = self.pool.get('account.journal')
        invoice_type = self._get_invoice_type(cr, uid, context=context)
        if invoice_type in ['in_refund', 'in_invoice']:
            journal_type = 'purchase'
        else:
            journal_type = 'sale'
        journals = journal_obj.search(cr, uid, [('type', '=', journal_type)])
        return journals and journals[0] or False

    def _get_invoice_type(self, cr, uid, context=None):
        if context is None:
            context = {}
        res_ids = context and context.get('active_ids', [])
        pick_obj = self.pool.get('stock.picking')
        pickings = pick_obj.browse(cr, uid, res_ids, context=context)
        pick = pickings and pickings[0]
        if not pick or not pick.move_lines:
            return 'out_invoice'
        type = pick.picking_type_id.code
        usage = pick.move_lines[0].location_id.usage if type == 'incoming' else pick.move_lines[0].location_dest_id.usage

        return INVOICE_TYPE_MAP.get((type, usage), ['out_invoice'])[0]

    _name = "stock.invoice.onshipping"
    _description = "Stock Invoice Onshipping"
    _columns = {
        'journal_id': fields.many2one('account.journal', 'Destination Journal', required=True),
        'group': fields.boolean("Group by partner"),
        'invoice_date': fields.date('Invoice Date'),
        'invoice_type': fields.selection(selection=[
            ('out_invoice', 'Create Customer Invoice'),
            ('in_invoice', 'Create Supplier Bill'),
            ('out_refund', 'Create Customer Refund'),
            ('in_refund', 'Create Supplier Refund'),
        ], string='Invoice type', readonly=True),
    }
    _defaults = {
        'journal_id': _get_journal,
        'invoice_type': _get_invoice_type,
    }

    def onchange_journal_id(self, cr, uid, ids, journal_id, context=None):
        if context is None:
            context = {}
        domain = {}
        value = {}
        active_id = context.get('active_id')
        if active_id:
            picking = self.pool['stock.picking'].browse(cr, uid, active_id, context=context)
            type = picking.picking_type_id.code
            usage = picking.move_lines[0].location_id.usage if type == 'incoming' else picking.move_lines[0].location_dest_id.usage
            invoice_types = INVOICE_TYPE_MAP.get((type, usage), ['out_invoice', 'in_invoice', 'out_refund', 'in_refund'])
            journal_types = ['purchase' if it in ['in_refund', 'in_invoice'] else 'sale' for it in invoice_types]
            domain['journal_id'] = [('type', 'in', journal_types)]
        if journal_id:
            journal = self.pool['account.journal'].browse(cr, uid, journal_id, context=context)
            value['journal_type'] = journal.type
        return {'value': value, 'domain': domain}

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        res = super(stock_invoice_onshipping, self).view_init(cr, uid, fields_list, context=context)
        pick_obj = self.pool.get('stock.picking')
        count = 0
        active_ids = context.get('active_ids',[])
        for pick in pick_obj.browse(cr, uid, active_ids, context=context):
            if pick.invoice_state != '2binvoiced':
                count += 1
        if len(active_ids) == count:
            raise UserError(_('None of these picking lists require invoicing.'))
        return res

    def open_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        
        invoice_ids = self.create_invoice(cr, uid, ids, context=context)
        if not invoice_ids:
            raise UserError(_('No invoice created!'))

        action_model = False
        action = {}
        
        inv_type = self.browse(cr, uid, ids[0], context=context).invoice_type
        data_pool = self.pool.get('ir.model.data')
        if inv_type in ["out_invoice", "out_refund"]:
            action_id = data_pool.xmlid_to_res_id(cr, uid, 'account.action_invoice_tree1')
        elif inv_type in ["in_invoice", "in_refund"]:
            action_id = data_pool.xmlid_to_res_id(cr, uid, 'account.action_invoice_tree2')

        if action_id:
            action_pool = self.pool['ir.actions.act_window']
            action = action_pool.read(cr, uid, action_id, context=context)
            action['domain'] = "[('id','in', ["+','.join(map(str,invoice_ids))+"])]"
            return action
        return True

    def create_invoice(self, cr, uid, ids, context=None):
        context = dict(context or {})
        picking_pool = self.pool.get('stock.picking')
        data = self.browse(cr, uid, ids[0], context=context)
        context['date_inv'] = data.invoice_date
        acc_journal = self.pool.get("account.journal")
        inv_type = data.invoice_type
        context['inv_type'] = inv_type

        active_ids = context.get('active_ids', [])
        res = picking_pool.action_invoice_create(cr, uid, active_ids,
              journal_id = data.journal_id.id,
              group = data.group,
              type = inv_type,
              context=context)
        return res
