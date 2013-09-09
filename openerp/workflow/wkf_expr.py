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

"""
Evaluate workflow code found in activity actions and transition conditions.
"""

import openerp
from openerp.tools.safe_eval import safe_eval as eval

class Env(dict):
    """
    Dictionary class used as an environment to evaluate workflow code (such as
    the condition on transitions).

    This environment provides sybmols for cr, uid, id, model name, model
    instance, column names, and all the record (the one obtained by browsing
    the provided ID) attributes.
    """
    def __init__(self, cr, uid, model, id):
        self.cr = cr
        self.uid = uid
        self.model = model
        self.id = id
        self.ids = [id]
        self.obj = openerp.registry(cr.dbname)[model]
        self.columns = self.obj._columns.keys() + self.obj._inherit_fields.keys()

    def __getitem__(self, key):
        if (key in self.columns) or (key in dir(self.obj)):
            res = self.obj.browse(self.cr, self.uid, self.id)
            return res[key]
        else:
            return super(Env, self).__getitem__(key)

def _eval_expr(cr, ident, workitem, lines):
    """
    Evaluate each line of ``lines`` with the ``Env`` environment, returning
    the value of the last line.
    """
    assert lines, 'You used a NULL action in a workflow, use dummy node instead.'
    uid, model, id = ident
    result = False
    for line in lines.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line == 'True':
            result = True
        elif line == 'False':
            result = False
        else:
            env = Env(cr, uid, model, id)
            result = eval(line, env, nocopy=True)
    return result

def execute_action(cr, ident, workitem, activity):
    """
    Evaluate the ir.actions.server action specified in the activity.
    """
    uid, model, id = ident
    ir_actions_server = openerp.registry(cr.dbname)['ir.actions.server']
    context = { 'active_model': model, 'active_id': id, 'active_ids': [id] }
    result = ir_actions_server.run(cr, uid, [activity['action_id']], context)
    return result

def execute(cr, ident, workitem, activity):
    """
    Evaluate the action specified in the activity.
    """
    return _eval_expr(cr, ident, workitem, activity['action'])

def check(cr, workitem, ident, transition, signal):
    """
    Test if a transition can be taken. The transition can be taken if:
    
    - the signal name matches,
    - the uid is SUPERUSER_ID or the user groups contains the transition's
      group,
    - the condition evaluates to a truish value.
    """
    if transition['signal'] and signal != transition['signal']:
        return False

    uid = ident[0]
    if uid != openerp.SUPERUSER_ID and transition['group_id']:
        registry = openerp.registry(cr.dbname)
        user_groups = registry['res.users'].read(cr, uid, [uid], ['groups_id'])[0]['groups_id']
        if transition['group_id'] not in user_groups:
            return False

    return _eval_expr(cr, ident, workitem, transition['condition'])


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

