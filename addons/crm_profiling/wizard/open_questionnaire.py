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
import pooler
import wizard
from tools import UpdateableStr, UpdateableDict

_QUEST_FORM = UpdateableStr()
_QUEST_FIELDS=UpdateableDict()

class open_questionnaire(wizard.interface):

    def _questionnaire_compute(self, cr, uid, data, context):
        pooler.get_pool(cr.dbname).get(data['model'])._questionnaire_compute(cr, uid, data, context)
        return {}


    def build_form(self, cr, uid, data, context):
        quest_form, quest_fields = pooler.get_pool(cr.dbname).get('crm_profiling.questionnaire').build_form(cr, uid, data, context)
        _QUEST_FORM. __init__(quest_form)
        _QUEST_FIELDS.__init__(quest_fields)
        return{}

    _questionnaire_choice_arch = '''<?xml version="1.0"?>
    <form string="Questionnaire">
        <field name="questionnaire_name"/>
    </form>'''

    _questionnaire_choice_fields = {
            'questionnaire_name': {'string': 'Questionnaire name', 'type': 'many2one', 'relation': 'crm_profiling.questionnaire', 'required': True },
    }

    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch': _questionnaire_choice_arch, 'fields': _questionnaire_choice_fields, 'state':[('end', 'Cancel','gtk-cancel'), ('open', 'Open Questionnaire','terp-camera_test')]}
        },
        'open': {
            'actions': [build_form],
            'result': {'type': 'form', 'arch':_QUEST_FORM, 'fields': _QUEST_FIELDS, 'state':[('end', 'Cancel','gtk-cancel'), ('compute', 'Save Data','terp-stock_format-scientific')]}
        },
        'compute': {
            'actions': [],
            'result': {'type': 'action', 'action': _questionnaire_compute, 'state':'end'}
        }
    }

open_questionnaire('open_questionnaire')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

