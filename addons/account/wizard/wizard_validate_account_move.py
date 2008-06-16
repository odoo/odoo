##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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
from osv import osv
import pooler

_journal_form = '''<?xml version="1.0"?>
<form string="Standard entries">
    <field name="journal_id"/>
</form>'''
_journal_fields = {
    'journal_id': {'string':'Journal', 'type':'many2one', 'relation':'account.journal', 'required':True},
}

def _validate_move(self, cr, uid, data, context={}):
    pool = pooler.get_pool(cr.dbname)
    move_obj = pool.get('account.move')
    ids_move = move_obj.search(cr,uid,[('state','=','draft'),('journal_id','=',data['form']['journal_id'])])
    if not ids_move:
        raise wizard.except_wizard('Warning', 'Specified Journal does not have any account move enties in draft state')
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
        raise wizard.except_wizard('Warning', 'Selected Move lines does not have any account move enties in draft state')
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