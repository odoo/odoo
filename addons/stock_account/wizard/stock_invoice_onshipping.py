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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class stock_invoice_onshipping(osv.osv_memory):
    def _get_journal(self, cr, uid, context=None):
        journal_obj = self.pool['account.journal']
        journal_ids = journal_obj.search(cr, uid, [('type', 'in', ('sale','sale_refund'))], limit=1)
        return journal_ids[0] if journal_ids else False

    _name = "stock.invoice.onshipping"
    _description = "Stock Invoice Onshipping"
    _columns = {
        'journal_id': fields.many2one('account.journal', 'Destination Journal', required=True, domain=[('type', 'in', ('sale','sale_refund'))]),
        'group': fields.boolean("Group by partner"),
        'inv_type': fields.selection([('out_invoice','Create Invoice'),('out_refund','Refund Invoice')], "Invoice Type"),
        'invoice_date': fields.date('Invoice Date'),
    }

    _defaults = {
        'journal_id' : _get_journal,
        'inv_type': lambda self,cr,uid,ctx: ctx.get('inv_type', 'out_invoice')
    }

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
            raise osv.except_osv(_('Warning!'), _('None of these picking lists require invoicing.'))
        return res

    def open_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        invoice_ids = self.create_invoice(cr, uid, ids, context=context)
        if not invoice_ids:
            raise osv.except_osv(_('Error!'), _('No invoice created!'))

        wizard = self.browse(cr, uid, ids[0], context=context)
        inv_type = wizard.inv_type

        action_model = False
        action = {}

        data_pool = self.pool.get('ir.model.data')
        if inv_type == "out_refund":
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree3")
        elif inv_type == "out_invoice":
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree1")

        if action_model:
            action_pool = self.pool[action_model]
            action = action_pool.read(cr, uid, action_id, context=context)
            action['domain'] = "[('id','in', ["+','.join(map(str,invoice_ids))+"])]"
            return action
        return True

    def create_invoice(self, cr, uid, ids, context=None):
        picking_pool = self.pool.get('stock.picking')
        wizard = self.browse(cr, uid, ids[0], context=context)

        context = dict(context or {})
        context['date_inv'] = wizard.invoice_date
        context['inv_type'] = wizard.inv_type

        active_ids = context.get('active_ids', [])
        res = picking_pool.action_invoice_create(cr, uid, active_ids,
              journal_id=wizard.journal_id.id,
              group=wizard.group,
              type=wizard.inv_type,
              context=context)
        return res

