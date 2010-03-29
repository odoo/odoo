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

from osv import fields, osv
from service import web_services
from tools.misc import UpdateableStr, UpdateableDict
from tools.translate import _
import netsvc
import pooler
import time
import wizard

class stock_invoice_onshipping(osv.osv_memory):
    _name = "stock.invoice.onshipping"
    _description = "Stock Invoice Onshipping"
    _columns = {
            'journal_id': fields.many2one('account.journal', 'Destination Journal', required=True),
            'group': fields.boolean("Group by partner"),
            'type': fields.selection([('out_invoice', 'Customer Invoice'),
                        ('in_invoice', 'Supplier Invoice'),
                        ('out_refund', 'Customer Refund'),
                        ('in_refund', 'Supplier Refund')] , 'Type', required=True),
            'invoice_date': fields.date('Invoiced date'),
            }

    def _get_type(self, cr, uid, context):
        """ 
             To get invoice type
            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs if we want more than one 
             @param context: A standard dictionary 
             
             @return: invoice type
        
        """                
        picking_obj = self.pool.get('stock.picking')
        usage = 'customer'
        pick = picking_obj.browse(cr, uid, context['active_id'])
        if pick.invoice_state == 'invoiced':
            raise osv.except_osv(_('UserError'), _('Invoice is already created.'))
        if pick.invoice_state == 'none':
            raise osv.except_osv(_('UserError'), _('Invoice cannot be created from Picking.'))
        if pick.move_lines:
            usage = pick.move_lines[0].location_id.usage

        if pick.type == 'out' and usage == 'supplier':
            type = 'in_refund'
        elif pick.type == 'out' and usage == 'customer':
            type = 'out_invoice'
        elif pick.type == 'in' and usage == 'supplier':
            type = 'in_invoice'
        elif pick.type == 'in' and usage == 'customer':
            type = 'out_refund'
        else:
            type = 'out_invoice'
        return type

    _defaults = {
            'type': _get_type,
        }

    def create_invoice(self, cr, uid, ids, context):
        """ 
             To create invoice
            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs if we want more than one 
             @param context: A standard dictionary 
             
             @return: invoice ids 
        
        """        
        result = []
        picking_obj = self.pool.get('stock.picking')
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        for onshipdata_obj in self.read(cr, uid, ids, ['journal_id', 'group', 'type', 'invoice_date']):
            if context.get('new_picking', False):
                onshipdata_obj[id] = onshipdata_obj.new_picking
                onshipdata_obj[ids] = onshipdata_obj.new_picking

            type = onshipdata_obj['type']
            context['date_inv'] = onshipdata_obj['invoice_date']
            res = picking_obj.action_invoice_create(cr, uid,context['active_ids'],
                  journal_id = onshipdata_obj['journal_id'],
                  group=onshipdata_obj['group'],
                  type=type,
                  context=context)
            invoice_ids = res.values()
            if not invoice_ids:
                raise  osv.except_osv(_('Error'), _('Invoice is not created'))

            if type == 'out_invoice':
                xml_id = 'action_invoice_tree1'
            elif type == 'in_invoice':
                xml_id = 'action_invoice_tree2'
            elif type == 'out_refund':
                xml_id = 'action_invoice_tree3'
            else:
                xml_id = 'action_invoice_tree4'

            result = mod_obj._get_id(cr, uid, 'account', xml_id)
            id = mod_obj.read(cr, uid, result, ['res_id'])
            result = act_obj.read(cr, uid, id['res_id'])
            result['res_id'] = invoice_ids
            return result

stock_invoice_onshipping()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

