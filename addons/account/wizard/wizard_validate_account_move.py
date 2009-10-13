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
from osv import osv
import pooler
from tools.translate import _

_journal_form = '''<?xml version="1.0"?>
<form string="Validate Account Entries">
    <separator string="Select Period and Journal for Validation" colspan="4"/>
    <field name="journal_id"/>
    <newline/>
    <field name="period_id"/>
    <separator string="Information" colspan="4"/>
    <label string="All draft account entries in this journal and period will be validated. It means you won't be able to modify their accouting fields." colspan="4"/>
</form>'''

_journal_fields = {
    'journal_id': {'string':'Journal', 'type':'many2one', 'relation':'account.journal', 'required':True},
    'period_id': {'string':'Period', 'type':'many2one', 'relation':'account.period', 'required':True, 'domain':"[('state','<>','done')]"},
}

def _validate_move(self, cr, uid, data, context={}):
    pool = pooler.get_pool(cr.dbname)
    move_obj = pool.get('account.move')
    ids_move = move_obj.search(cr,uid,[('state','=','draft'),('journal_id','=',data['form']['journal_id']),('period_id','=',data['form']['period_id'])])
    if not ids_move:
        raise wizard.except_wizard(_('Warning'), _('Specified Journal does not have any account move entries in draft state for this period'))
    res = move_obj.button_validate(cr, uid, ids_move, context)
    return {}

class validate_account_move(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':_journal_form, 'fields':_journal_fields, 'state':[('end','Cancel'),('validate','Validate')]}
        },
        'validate': {
            'actions': [_validate_move],
            'result': {'type': 'state', 'state':'end'}
        },
    }
validate_account_move('account.move.validate')

def _validate_move_lines(self, cr, uid, data, context={}):
    move_ids = []
    pool = pooler.get_pool(cr.dbname)
    move_line_obj = pool.get('account.move.line')
    move_obj = pool.get('account.move')
    data_line = move_line_obj.browse(cr,uid,data['ids'],context)
    for line in data_line:
        if line.move_id.state=='draft':
            move_ids.append(line.move_id.id)
    move_ids = list(set(move_ids))
    if not move_ids:
        raise wizard.except_wizard(_('Warning'), _('Selected Move lines does not have any account move enties in draft state'))
    res = move_obj.button_validate(cr, uid, move_ids, context)
    return {}

class validate_account_move_lines(wizard.interface):
    states = {
        'init': {
            'actions': [_validate_move_lines],
            'result': {'type': 'state', 'state':'end'}
        },
    }
validate_account_move_lines('account.move_line.validate')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

