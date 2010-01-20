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
<form string="Print Survey">
    <separator string="Print Option" colspan="4"/>
    <field name="orientation" colspan="4"/>
    <field name="paper_size" colspan="4"/>
    <field name="survey_title" colspan="4"/>
    <field name="page_number" colspan="4"/>
    <field name="without_pagebreak" colspan="4"/>
</form>'''

_survey_fields = {
    'orientation':{
        'string':"Orientation",
        'type':'selection',
        'selection':[('vertical','Portrait(Vertical)'),
                     ('horizontal','Landscape(Horizontal)')],
        'default': lambda *a:'vertical'},
    'paper_size':{
        'string':"Paper Size",
        'type':'selection',
        'selection':[('letter','Letter (8.5" x 11")'),
                     ('legal','Legal (8.5" x 14")'),
                     ('a4','A4 (210mm x 297mm)')],
        'default': lambda *a:'letter'},
    'survey_title': {'string':'Include Survey Title', 'type':'boolean', 'default':lambda *a: 0},
    'page_number': {'string':'Include Page Numbers', 'type':'boolean', 'default':lambda *a: 0},
    'without_pagebreak': {'string':'Print Without Page Breaks', 'type':'boolean', 'default':lambda *a: 0},
    }

class print_survey_wizard(wizard.interface):
    states = {
        'init' : {
            'actions' : [],
            'result' : {'type' : 'form', 'arch' :_survey_form, 'fields' :_survey_fields,\
                             'state' : [('end', 'Cancel', 'gtk-cancel'), ('print', 'Print', 'gtk-print')]}
                },
        'print': {
            'actions': [],
            'result': {'type':'print', 'report':'survey.form', 'state':'end'}
        }
    }
print_survey_wizard('wizard.print.survey')
