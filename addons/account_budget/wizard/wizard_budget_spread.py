# -*- coding: utf-8 -*-
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

_spread_form = '''<?xml version="1.0"?>
<form string="Spread">
    <field name="fiscalyear"/>
    <field name="amount"/>
</form>'''

_spread_fields = {
    'fiscalyear': {'string':'Fiscal Year', 'type':'many2one', 'relation':'account.fiscalyear', 'required':True},
    'amount': {'string':'Amount', 'type':'float', 'digits':(16,2)},
}

class wizard_budget_spread(wizard.interface):
    def _spread(self, cr, uid, data, context):
        service = netsvc.LocalService("object_proxy")
        form = data['form']
        res = service.execute(cr.dbname, uid, 'account.budget.post', 'spread', data['ids'], form['fiscalyear'], form['amount'])
        return {}

    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':_spread_form, 'fields':_spread_fields, 'state':[('end','Cancel'),('spread','Spread')]}
        },
        'spread': {
            'actions': [_spread],
            'result': {'type':'state', 'state':'end'}
        }
    }
wizard_budget_spread('account.budget.spread')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

