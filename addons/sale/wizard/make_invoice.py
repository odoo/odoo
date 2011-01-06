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
import netsvc
import pooler

invoice_form = """<?xml version="1.0"?>
<form string="Create invoices">
    <separator colspan="4" string="Do you really want to create the invoice(s) ?" />
    <field name="grouped" />
</form>
"""

invoice_fields = {
    'grouped' : {'string':'Group the invoices', 'type':'boolean', 'default': lambda x,y,z: False}
}

ack_form = """<?xml version="1.0"?>
<form string="Create invoices">
    <separator string="Invoices created" />
</form>"""

ack_fields = {}

def _makeInvoices(self, cr, uid, data, context):
    order_obj = pooler.get_pool(cr.dbname).get('sale.order')
    newinv = []

    order_obj.action_invoice_create(cr, uid, data['ids'], data['form']['grouped'])
    for id in data['ids']:
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'sale.order', id, 'manual_invoice', cr)

    for o in order_obj.browse(cr, uid, data['ids'], context):
        for i in o.invoice_ids:
            newinv.append(i.id)
    pool = pooler.get_pool(cr.dbname)
    mod_obj = pool.get('ir.model.data')
    act_obj = pool.get('ir.actions.act_window')
    xml_id='action_invoice_tree5'
    result = mod_obj._get_id(cr, uid, 'account', xml_id)
    id = mod_obj.read(cr, uid, result, ['res_id'])['res_id']
    result = act_obj.read(cr, uid, id)
    result['domain'] ="[('id','in', ["+','.join(map(str,newinv))+"])]"
    return result
    #return {
    #    'domain': "[('id','in', ["+','.join(map(str,newinv))+"])]",
    #    'name': 'Invoices',
    #    'view_type': 'form',
    #    'view_mode': 'tree,form',
    #    'res_model': 'account.invoice',
    #    'view_id': False,
    #    'context': "{'type':'out_refund'}",
    #    'type': 'ir.actions.act_window'
    #}
    #return {}

class make_invoice(wizard.interface):
    states = {
        'init' : {
            'actions' : [],
            'result' : {'type' : 'form',
                    'arch' : invoice_form,
                    'fields' : invoice_fields,
                    'state' : [('end', 'Cancel'),('invoice', 'Create invoices') ]}
        },
        'invoice' : {
            'actions' : [],
            'result' : {'type' : 'action',
                    'action' : _makeInvoices,
                    'state' : 'end'}
        },
    }
make_invoice("sale.order.make_invoice")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

