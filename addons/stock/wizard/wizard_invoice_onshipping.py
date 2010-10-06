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

import wizard
import pooler
from tools.translate import _

invoice_form = """<?xml version="1.0"?>
<form string="Create invoices">
    <separator colspan="4" string="Create invoices" />
    <field name="journal_id"/>
    <newline/>
    <field name="group"/>
    <newline/>
    <field name="type"/>
</form>
"""

invoice_fields = {
    'journal_id': {
        'string': 'Destination Journal',
        'type': 'many2one',
        'relation': 'account.journal',
        'required': True
    },
    'group': {
        'string': 'Group by partner',
        'type': 'boolean'
    },
    'type': {
        'string': 'Type',
        'type': 'selection',
        'selection': [
            ('out_invoice', 'Customer Invoice'),
            ('in_invoice', 'Supplier Invoice'),
            ('out_refund', 'Customer Refund'),
            ('in_refund', 'Supplier Refund'),
            ],
        'required': True
    },
}


def _get_type(obj, cr, uid, data, context=None):
    picking_obj = pooler.get_pool(cr.dbname).get('stock.picking')
    src_usage = dest_usage = None
    pick = picking_obj.browse(cr, uid, data['id'], context=context)
    if pick.invoice_state == 'invoiced':
        raise wizard.except_wizard(_('UserError'), _('Invoice is already created.'))
    if pick.invoice_state == 'none':
        raise wizard.except_wizard(_('UserError'), _('Invoice cannot be created from Packing.'))

    if pick.move_lines:
        src_usage = pick.move_lines[0].location_id.usage
        dest_usage = pick.move_lines[0].location_dest_id.usage

    if pick.type == 'out' and dest_usage == 'supplier':
        type = 'in_refund'
    elif pick.type == 'out' and dest_usage == 'customer':
        type = 'out_invoice'
    elif pick.type == 'in' and src_usage == 'supplier':
        type = 'in_invoice'
    elif pick.type == 'in' and src_usage == 'customer':
        type = 'out_refund'
    else:
        type = 'out_invoice'
    return {'type': type}


def _create_invoice(obj, cr, uid, data, context=None):
    if context is None:
        context = {}
    if data['form'].get('new_picking', False):
        data['id'] = data['form']['new_picking']
        data['ids'] = [data['form']['new_picking']]
    pool = pooler.get_pool(cr.dbname)
    picking_obj = pooler.get_pool(cr.dbname).get('stock.picking')
    mod_obj = pool.get('ir.model.data')
    act_obj = pool.get('ir.actions.act_window')

    type = data['form']['type']

    res = picking_obj.action_invoice_create(cr, uid, data['ids'],
            journal_id=data['form']['journal_id'], group=data['form']['group'],
            type=type, context=context)

    invoice_ids = res.values()
    if not invoice_ids:
        raise wizard.except_wizard(_('Error'), _('Invoice is not created'))

    if type == 'out_invoice':
        xml_id = 'action_invoice_tree5'
    elif type == 'in_invoice':
        xml_id = 'action_invoice_tree8'
    elif type == 'out_refund':
        xml_id = 'action_invoice_tree10'
    else:
        xml_id = 'action_invoice_tree12'

    result = mod_obj._get_id(cr, uid, 'account', xml_id)
    id = mod_obj.read(cr, uid, result, ['res_id'], context=context)
    result = act_obj.read(cr, uid, id['res_id'], context=context)
    result['res_id'] = invoice_ids
    result['context'] = context
    return result


class make_invoice_onshipping(wizard.interface):
    states = {
        'init': {
            'actions': [_get_type],
            'result': {
                'type': 'form',
                'arch': invoice_form,
                'fields': invoice_fields,
                'state': [
                    ('end', 'Cancel'),
                    ('create_invoice', 'Create invoice')
                ]
            }
        },
        'create_invoice': {
            'actions': [],
            'result': {
                'type': 'action',
                'action': _create_invoice,
                'state': 'end'
            }
        },
    }

make_invoice_onshipping("stock.invoice_onshipping")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
