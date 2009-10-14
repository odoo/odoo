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

import wizard
import pooler

form = '''<?xml version="1.0"?>
<form string="Print Journal">
    <field name="journal_id"/>
    <field name="period_id"/>
    <field name="sort_selection"/>
</form>'''

fields = {
  'journal_id': {'string': 'Journal', 'type': 'many2many', 'relation': 'account.journal', 'required': True},
  'period_id': {'string': 'Period', 'type': 'many2many', 'relation': 'account.period', 'required': True},
  'sort_selection':{
        'string':"Entries Sorted By",
        'type':'selection',
        'selection':[('date','By date'),('ref','Reference Number')],
        'required':True,
        'default': lambda *a: 'date',
    },

}

def _check_data(self, cr, uid, data, *args):
    period_id = data['form']['period_id'][0][2]
    journal_id=data['form']['journal_id'][0][2]

    if type(period_id)==type([]):
        
        ids_final = []

        for journal in journal_id:
            for period in period_id:
                ids_journal_period = pooler.get_pool(cr.dbname).get('account.journal.period').search(cr,uid, [('journal_id','=',journal),('period_id','=',period)])

                if ids_journal_period:
                    ids_final.append(ids_journal_period)

            if not ids_final:
                raise wizard.except_wizard(_('No Data Available'), _('No records found for your selection!'))
    return data['form']

class wizard_print_journal(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch': form, 'fields': fields, 'state': (('end', 'Cancel'), ('print', 'Print'))},
        },
        'print': {
            'actions': [_check_data],
            'result': {'type':'print', 'report':'account.journal.period.print.wiz', 'state':'end'},
        },
    }
wizard_print_journal('account.print.journal.report')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

