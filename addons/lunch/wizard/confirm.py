# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
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

