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
    <field name="group"/>  
</form>
"""
invoice_fields = {	
	'group': {
		'string': 'Group by partner invoice address',
		'type':'boolean'
	},
}

ack_form = """<?xml version="1.0"?>
<form string="Create invoices">
    <separator string="Invoices created" />    
</form>"""

ack_fields = {}

def _makeInvoices(self, cr, uid, data, context):
    order_obj = pooler.get_pool(cr.dbname).get('mrp.repair')       
    newinv = order_obj.action_invoice_create(cr, uid, data['ids'],group=data['form']['group'],context=context)    
        
    return {
        'domain': [('id','in', newinv.values())],
        'name': 'Invoices',
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'account.invoice',
        'view_id': False,
        'context': "{'type':'out_refund'}",
        'type': 'ir.actions.act_window'
    }
    

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
make_invoice("mrp.repair.make_invoice")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

