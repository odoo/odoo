# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import wizard
import netsvc
import ir
import pooler

confirm_order_form = """<?xml version="1.0"?>
<form title="Confirm">
    <separator string="Orders Confirmation" colspan="4"/>
    <field name="confirm_cashbox"/>
    <newline/>
</form>
"""

confirm_order_fields = {
    'confirm_cashbox': {'string':'Name of box', 'type':'many2one', 'required':True, 'relation':'lunch.cashbox' },
}

def _confirm(self,cr,uid,data,context):
    pool= pooler.get_pool(cr.dbname)
    order_ref = pool.get('lunch.order')
    order_ref.confirm(cr,uid,data['ids'],data['form']['confirm_cashbox'],context)
    return {}

class order_confirm(wizard.interface):
    states = {
        'init': {
            'action':[],
            'result':{'type' : 'form', 'arch' : confirm_order_form, 'fields' : confirm_order_fields, 'state' : [('end', 'Cancel'),('go', 'Confirm Order') ]},
        },
        'go' : {
            'actions' : [_confirm],
            'result' : {'type' : 'state', 'state' : 'end'}
        },
    }
order_confirm('lunch.order.confirm')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

