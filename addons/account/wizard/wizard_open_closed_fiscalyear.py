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
from osv import fields, osv
from tools.translate import _

form = """<?xml version="1.0"?>
<form string="Choose Fiscal Year">
    <field name="fyear_id" domain="[('state','=','draft')]"/>
</form>
"""

fields = {
    'fyear_id': {'string': 'Fiscal Year to Open', 'type': 'many2one', 'relation': 'account.fiscalyear', 'required': True},
}

def _remove_entries(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    data_fyear = pool.get('account.fiscalyear').browse(cr,uid,data['form']['fyear_id'])
    if not data_fyear.end_journal_period_id:
        raise wizard.except_wizard(_('Error'), _('No journal for ending writing has been defined for the fiscal year'))
    period_journal = data_fyear.end_journal_period_id
    ids_move = pool.get('account.move').search(cr,uid,[('journal_id','=',period_journal.journal_id.id),('period_id','=',period_journal.period_id.id)])
    if ids_move:
        cr.execute('delete from account_move where id in %s', (tuple(ids_move),))
    return {}

class open_closed_fiscal(wizard.interface):
    states = {
        'init' : {
            'actions' : [],
            'result': {
                'type': 'form', 
                'arch': form,
                'fields': fields, 
                'state':[('end','Cancel'),('open','Open')]
            }
        },
        'open': {
            'actions': [],
            'result': {
                'type':'action', 
                'action':_remove_entries, 
                'state':'end'
            },
        },
    }
open_closed_fiscal("account.open_closed_fiscalyear")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

