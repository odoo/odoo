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
        res = self._get_journal_id(cr, uid, context=context)
        if res:
            return res[0][0]
        return False

    def _get_journal_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        journal_obj = self.pool.get('account.journal')
        res_ids = context and context.get('active_ids', [])
        pick_obj = self.pool.get('stock.picking')
        pickings = pick_obj.browse(cr, uid, res_ids, context=context)
        vals = []
        for pick in pickings:
            if not pick.move_lines:
                continue
            src_usage = pick.move_lines[0].location_id.usage
            dest_usage = pick.move_lines[0].location_dest_id.usage
            type = pick.picking_type_id.code
            if type == 'outgoing' and dest_usage == 'supplier':
                journal_type = 'purchase_refund'
            elif type == 'outgoing' and dest_usage == 'customer':
                journal_type = 'sale'
            elif type == 'incoming' and src_usage == 'supplier':
                journal_type = 'purchase'
            elif type == 'incoming' and src_usage == 'customer':
                journal_type = 'sale_refund'
            else:
                journal_type = 'sale'
            journals = journal_obj.search(cr, uid, [('type', '=', journal_type)])
            for jr_type in journal_obj.browse(cr, uid, journals, context=context):
                t1 = str(jr_type.id),jr_type.name
                print t1
                if t1 not in vals:
                    vals.append(t1)
        return vals

    _name = "stock.invoice.onshipping"
    _description = "Stock Invoice Onshipping"
    _columns = {
        'journal_id': fields.selection(_get_journal_id, 'Destination Journal',required=True),
        'group': fields.boolean("Group by partner"),
        'inv_type': fields.selection([('out_invoice','Create Invoice'),('out_refund','Refund Invoice')], "Invoice Type"),
        'invoice_date': fields.date('Invoice Date'),
        #'inv_t': fields.selection([('in_invoice', ''), ]),
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

        data = self.browse(cr, uid, ids[0], context=context)

        action_model = False
        action = {}
        acc_journal = self.pool.get("account.journal")
        journal = acc_journal.browse(cr, uid, int(data.journal_id), context=context)
        journal2type = {'sale':'out_invoice', 'purchase':'in_invoice' , 'sale_refund':'out_refund', 'purchase_refund':'in_refund'}
        inv_type = journal2type.get(journal.type) or 'out_invoice'
        data_pool = self.pool.get('ir.model.data')
        if inv_type == "out_invoice":
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree1")
        elif inv_type == "in_invoice":
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree2")
        elif inv_type == "out_refund":
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree3")
        elif inv_type == "in_refund":
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree4")

        if action_model:
            action_pool = self.pool[action_model]
            action = action_pool.read(cr, uid, action_id, context=context)
            action['domain'] = "[('id','in', ["+','.join(map(str,invoice_ids))+"])]"
            return action
        return True

    def create_invoice(self, cr, uid, ids, context=None):
        context = context or {}
        picking_pool = self.pool.get('stock.picking')
        data = self.browse(cr, uid, ids[0])
        journal2type = {'sale':'out_invoice', 'purchase':'in_invoice', 'sale_refund':'out_refund', 'purchase_refund':'in_refund'}
        context['date_inv'] = data.invoice_date
        acc_journal = self.pool.get("account.journal")
        journal = acc_journal.browse(cr, uid, int(data.journal_id), context=context)
        inv_type = journal2type.get(journal.type) or 'out_invoice'
        context['inv_type'] = inv_type

        active_ids = context.get('active_ids', [])
        res = picking_pool.action_invoice_create(cr, uid, active_ids,
              journal_id = data.journal_id,
              group = data.group,
              type = inv_type,
              context=context)
        return res

