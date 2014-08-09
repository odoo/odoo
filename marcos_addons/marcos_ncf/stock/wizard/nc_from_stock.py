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
import ast
import datetime


class marcos_stock_invoice_onshipping(osv.osv_memory):

    def _get_journal(self, cr, uid, context=None):
        res = self._get_journal_id(cr, uid, context=context)
        if res:
            return res[0][0]
        return False

    def _get_journal_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        model = context.get('active_model')
        if not model or 'stock.picking' not in model:
            return []

        model_pool = self.pool.get(model)
        journal_obj = self.pool.get('account.journal')
        res_ids = context and context.get('active_ids', [])
        vals = []
        browse_picking = model_pool.browse(cr, uid, res_ids, context=context)

        for pick in browse_picking:
            if not pick.move_lines:
                continue
            journal_type = 'purchase_refund'
            value = journal_obj.search(cr, uid, [('type', '=',journal_type )])
            for jr_type in journal_obj.browse(cr, uid, value, context=context):
                t1 = jr_type.id,jr_type.name
                if t1 not in vals:
                    vals.append(t1)
        return vals

    _name = "marcos.stock.invoice.onshipping"
    _description = "Marcos Stock Invoice Onshipping"

    _columns = {
        'journal_id': fields.selection(_get_journal_id, 'Destination Journal',required=True),
        'group': fields.boolean("Group by partner"),
        'invoice_date': fields.date('Invoiced date'),
    }

    _defaults = {
        'journal_id' : _get_journal,
    }

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        res = super(marcos_stock_invoice_onshipping, self).view_init(cr, uid, fields_list, context=context)
        return res

    def open_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        invoice_ids = []
        data_pool = self.pool.get('ir.model.data')
        res = self.create_invoice(cr, uid, ids, context=context)

        invoice_ids += res.values()
        inv_type = 'in_refund'
        action_model = False

        inv_obj = self.pool.get('account.invoice')
        purchase_order_name = self.pool.get('purchase.order').read(cr, uid, context.get('search_default_purchase_id', False), ['name'])['name']
        parent_id = inv_obj.search(cr, uid, [('origin', '=', purchase_order_name), ('type', '=', 'in_invoice')])[0]
        reference_type = inv_obj.read(cr, uid, parent_id, ['reference_type'])['reference_type']
        self.pool.get('account.invoice').write(cr, uid, invoice_ids, {'parent_id': parent_id, 'reference_type': reference_type})

        ord_ids = context['active_ids']
        pick_obj = self.pool.get('stock.picking')
        for pick in pick_obj.browse(cr, uid, ord_ids, context=context):
            ids2 = [move.id for move in pick.move_lines]
            self.pool.get('stock.move').action_cancel(cr, uid, ids2, context)
        pick_obj.write(cr, uid, ord_ids, {'state': 'cancel', 'invoice_state': 'none'})

        action = {}
        if not invoice_ids:
            raise osv.except_osv(_('Error!'), _('Please create Invoices open_invoice.'))
        if inv_type == "out_invoice":
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree1")
        elif inv_type == "in_invoice":
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree2")
        elif inv_type == "out_refund":
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree3")
        elif inv_type == "in_refund":
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree4")
        if action_model:
            action_pool = self.pool.get(action_model)
            action = action_pool.read(cr, uid, action_id, context=context)
            action['domain'] = "[('id','in', ["+','.join(map(str,invoice_ids))+"])]"
        return action

    def create_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        picking_pool = self.pool.get('stock.picking')
        onshipdata_obj = self.read(cr, uid, ids, ['journal_id', 'group', 'invoice_date'])
        if context.get('new_picking', False):
            onshipdata_obj['id'] = onshipdata_obj.new_picking
            onshipdata_obj[ids] = onshipdata_obj.new_picking
        context['date_inv'] = onshipdata_obj[0]['invoice_date']
        active_ids = context.get('active_ids', [])
        inv_type = 'in_refund'
        context['inv_type'] = inv_type
        if isinstance(onshipdata_obj[0]['journal_id'], tuple):
            onshipdata_obj[0]['journal_id'] = onshipdata_obj[0]['journal_id'][0]
        context.update({'active_model': 'stock.picking.out', 'default_type': 'out'})
        res = picking_pool.action_invoice_create(cr, uid, active_ids,
              journal_id = onshipdata_obj[0]['journal_id'],
              group = onshipdata_obj[0]['group'],
              type = inv_type,
              context=context)
        return res

marcos_stock_invoice_onshipping()

class stock_return_picking(osv.osv_memory):
    _inherit = 'stock.return.picking'

    _columns = {
        'auto_pickin_action': fields.boolean("Auto"),
    }

    def default_get(self, cr, uid, fields, context=None):
        res = super(stock_return_picking, self).default_get(cr, uid, fields, context)
        res.update({'invoice_state': '2binvoiced'})
        return res

    def create_returns(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        res = super(stock_return_picking, self).create_returns(cr, uid, ids, context)
        if context.get("auto_pickin_action", False):

            piking_target_ids = ast.literal_eval(res['domain'])[0][2]
            picking_target = self.pool.get(res['res_model'])
            picking_target.write(cr, uid, piking_target_ids, {'auto_picking': True})

            picking_source = self.pool.get(context['active_model'])
            picking_source_data = picking_source.read(cr, uid, context["active_id"], ["origin", "date_invoice"])
            origin = picking_source_data["origin"]
            inv_obj = self.pool.get("account.invoice")
            inv_ids = inv_obj.search(cr, uid, [("origin", "=", origin)], context=context)
            context.update({"active_model": res["res_model"],
                            "active_ids": piking_target_ids,
                            "active_id": piking_target_ids[0]})

            view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'view_stock_invoice_onshipping')[1]
            wizard = {
                'name': 'Generar nota de credito',
                'view_mode': 'form',
                'view_id': False,
                'views': [(view_id, 'form')],
                'view_type': 'form',
                'res_model': 'stock.invoice.onshipping',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context
            }
            return wizard
