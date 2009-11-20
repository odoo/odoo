# -*- coding: utf-8 -*-
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

import time
import wizard

_form = '''<?xml version="1.0"?>
<form string="Select period">
    <separator string="Cost Legder for period" colspan="4"/>
    <field name="date1"/>
    <field name="date2"/>
    <separator string="and Journals" colspan="4"/>
    <field name="journal" colspan="4"/>
</form>'''

_fields = {
    'date1': {'string':'Start of period', 'type':'date', 'required':True, 'default': lambda *a: time.strftime('%Y-01-01')},
    'date2': {'string':'End of period', 'type':'date', 'required':True, 'default': lambda *a: time.strftime('%Y-%m-%d')},
    'journal': {'string':'Journals','type':'many2many', 'relation':'account.analytic.journal'},
}


class wizard_report(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': _form,
                'fields': _fields,
                'state': [
                    ('end','Cancel'),
                    ('report','Print')
                ]
            }
        },
        'report': {
            'actions': [],
            'result': {
                'type': 'print',
                'report': 'account.analytic.account.quantity_cost_ledger',
                'state': 'end'
            }
        },
    }

wizard_report('account.analytic.account.quantity_cost_ledger.report')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

