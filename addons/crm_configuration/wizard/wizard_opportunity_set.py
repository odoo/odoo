# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: makesale.py 1183 2005-08-23 07:43:32Z pinky $
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

from mx.DateTime import now

import wizard
import netsvc
import ir
import pooler

case_form = """<?xml version="1.0"?>
<form string="Convert To Opportunity">
    <field name="name"/>
    <newline/>
    <field name="planned_revenue"/>
    <field name="probability"/>
</form>"""

case_fields = {
    'name': {'type':'char', 'size':64, 'string':'Opportunity Summary'},
    'planned_revenue': {'type':'float', 'digits':(16,2), 'string': 'Expected Revenue'},
    'probability': {'type':'float', 'digits':(16,2), 'string': 'Success Probability'},
}


class make_opportunity(wizard.interface):

    def _selectopportunity(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        case_obj = pool.get('crm.case')
        for case in case_obj.browse(cr, uid, data['ids']):
            if not case.partner_id:
                raise wizard.except_wizard("Warning !",
                    _('You must assign a partner to this lead before converting to opportunity.\n' \
                  'You can use the convert to partner button.'))
        return {'name': case.name, 'probability': case.probability or 20.0, 'planned_revenue':case.planned_revenue}

    def _makeOrder(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        section_obj = pool.get('crm.case.section')
        data_obj = pool.get('ir.model.data')
        id = section_obj.search(cr, uid, [('code','=','oppor')], context=context)
        if not id:
            raise wizard.except_wizard(_("Error !"),
                _('You did not installed the opportunities tracking when you configured the crm_configuration module.' \
                  '\nI can not convert the lead to an opportunity, you must create a section with the code \'oppor\'.'
                  ))
        id = id[0]

        id2 = data_obj._get_id(cr, uid, 'crm_configuration', 'crm_case_form_view_oppor')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id


        case_obj = pool.get('crm.case')
        case_obj._history(cr, uid, case_obj.browse(cr, uid, [data['id']]), 'convert')
        case_obj.write(cr, uid, data['ids'], {
            'section_id': id,
            'name': data['form']['name'],
            'planned_revenue': data['form']['planned_revenue'],
            'probability': data['form']['probability'],
        })
        value = {
            'domain': "[]",
            'name': _('Opportunity'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'crm.case',
            'res_id': int(data['ids'][0]),
            'view_id': False,
            'views': [(id2,'form'),(False,'tree'),(False,'calendar'),(False,'graph')],
            'type': 'ir.actions.act_window',
        }
        return value

    states = {
        'init': {
            'actions': [_selectopportunity],
            'result': {'type': 'form', 'arch': case_form, 'fields': case_fields,
                'state' : [('end', 'Cancel', 'gtk-cancel'),('confirm', 'Create Opportunity', 'gtk-go-forward')]}
        },
        'confirm': {
            'actions': [],
            'result': {'type': 'action', 'action': _makeOrder, 'state': 'end'}
        }
    }

make_opportunity('crm.case.opportunity_set')

