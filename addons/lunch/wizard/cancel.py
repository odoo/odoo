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

cancel_form = """<?xml version="1.0"?>
<form string="Cancel Order">
    <label string="Are you sure you want to cancel this order ?"/>
</form>"""


cancel_fields = {
}

def _cancel(self,cr,uid,data,context):
    return pooler.get_pool(cr.dbname).get('lunch.order').lunch_order_cancel(cr,uid,data['ids'],context)

class order_cancel(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':cancel_form, 'fields':cancel_fields, 'state':[('end','No'),('cancel','Yes')]}
        },
        'cancel': {
            'actions': [_cancel],
            'result': {'type':'state', 'state':'end'}
        }
    }
order_cancel('lunch.order.cancel')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

