# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from tools.translate import _

rule_form = '''<?xml version="1.0"?>
<form string="Rules" colspan="4">
    <group colspan="4" attrs="{'invisible':[('deactivate','=',True)]}">
        <field name="activate"/>
    </group>
    <group colspan="4" attrs="{'invisible':[('activate','=',True)]}">
        <field name="deactivate"/>
    </group>
</form>'''

rule_fields = {
    'activate': {'string': 'Activate', 'type': 'boolean'},
    'deactivate': {'string': 'Deactivate', 'type': 'boolean'}
}

_rules_end = '''<?xml version="1.0"?>
<form string="Result">
    <label string="Action completed successfully !" colspan="4"/>    
</form>'''

class rules_activate_all(wizard.interface):
    def _check(self, cr, uid, data, context):
        actobj = pooler.get_pool(cr.dbname).get('base.action.rule')
        cronobj = pooler.get_pool(cr.dbname).get('ir.cron')
        cr.execute('select id, active from ir_cron where model=\'base.action.rule\'')
        crons = cr.fetchall()[0]
        check = actobj.search(cr, uid, [])
        if not check:
            cronobj.write(cr, uid, crons[0], {'active': False})
            raise wizard.except_wizard(_('Warning !'),_('No Rules defined !'))
        return {}
    
    def _activate_all(self, cr, uid, data, context):
        actobj = pooler.get_pool(cr.dbname).get('base.action.rule')
        if data['form']['activate']:
            actids = actobj.search(cr, uid, [('state','=','deactivate')])
            if actids:
                actobj.button_activate_rule(cr, uid, actids)
            else:
                raise wizard.except_wizard(_('Error'),_('All rules are already active.'))
        elif data['form']['deactivate']:
            actids = actobj.search(cr, uid, [('state','=','activate')])
            if actids:
                actobj.button_deactivate_rule(cr, uid, actids)
            else:
                raise wizard.except_wizard(_('Error'),_('All rules are already deactivated.'))
        else:
            raise wizard.except_wizard(_('Warning !'),_('No Action Performed !'))
        return {}

    states = {
        'init': {
            'actions': [_check],
            'result': {'type': 'form', 'arch': rule_form, 'fields': rule_fields, 'state':[('end','Cancel','gtk-cancel'),('ok','Ok','gtk-go-forward')]}
        },
        'ok': {
            'actions': [_activate_all],
            'result': {'type': 'form', 'arch': _rules_end,
                'fields': {},
                'state': (
                    ('end', 'Close','gtk-close'),
                )
            },
        },
    }
rules_activate_all('base.action.rule.activate.all')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
