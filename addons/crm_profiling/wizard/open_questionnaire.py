# -*- encoding: utf-8 -*-
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
            'result': {'type': 'form', 'arch': _questionnaire_choice_arch, 'fields': _questionnaire_choice_fields, 'state':[('end', 'Cancel'), ('open', 'Open Questionnaire')]}
        },
        'open': {
            'actions': [build_form],
            'result': {'type': 'form', 'arch':_QUEST_FORM, 'fields': _QUEST_FIELDS, 'state':[('end', 'Cancel'), ('compute', 'Save Data')]}
        },
        'compute': {
            'actions': [],
            'result': {'type': 'action', 'action': _questionnaire_compute, 'state':'end'}
        }
    }

open_questionnaire('open_questionnaire')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

