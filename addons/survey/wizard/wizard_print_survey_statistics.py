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
import time
import pooler
from random import choice
import string
import tools
from tools.translate import _

_survey_form = '''<?xml version="1.0"?>
<form string="Print Survey Statistics">
    <field name="survey_ids" colspan="4" nolabel="1"/>
</form>'''

_survey_fields = {
    'survey_ids': {'string': 'Survey', 'type': 'many2many', 'relation': 'survey','required':'1'},
    }

class print_survey_statistics_wizard(wizard.interface):
    states = {
        'init' : {
            'actions' : [],
            'result' : {'type' : 'form', 'arch' :_survey_form, 'fields' :_survey_fields,\
                             'state' : [('end', 'Cancel', 'gtk-cancel'), ('print', 'Print', 'gtk-print')]}
                },
        'print': {
            'actions': [],
            'result': {'type':'print', 'report':'survey.analysis', 'state':'end'}
        }
    }
print_survey_statistics_wizard('wizard.print.survey.statistics')
