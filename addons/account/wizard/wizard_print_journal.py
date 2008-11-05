# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

class wizard_print_journal(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch': form, 'fields': fields, 'state': (('end', 'Cancel'), ('print', 'Print'))},
        },
        'print': {
            'actions': [],
            'result': {'type':'print', 'report':'account.journal.period.print.wiz', 'state':'end'},
        },
    }
wizard_print_journal('account.print.journal.report')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

