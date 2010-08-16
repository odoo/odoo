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

from mx.DateTime import now

import wizard
import netsvc
import ir
import pooler
from tools.translate import _

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
                raise wizard.except_wizard(_('Warning !'),
                    _('You must assign a partner to this lead before converting to opportunity.\n' \
                  'You can use the convert to partner button.'))
        return {'name': case.name, 'probability': case.probability or 20.0, 'planned_revenue':case.planned_revenue}

    def _makeOrder(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        section_obj = pool.get('crm.case.section')
        data_obj = pool.get('ir.model.data')
        id = section_obj.search(cr, uid, [('code','=','oppor')], context=context)
        if not id:
            raise wizard.except_wizard(_('Error !'),
                _('You did not install the opportunities tracking when you configured the crm_configuration module.' \
                  '\nI can not convert the lead to an opportunity, you must create a section with the code \'oppor\'.'
                  ))
        id = id[0]

        id2 = data_obj._get_id(cr, uid, 'crm_configuration', 'crm_case_form_view_oppor')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id

        stage_ids = pool.get('crm.case.stage').search(cr, uid, [('name','=','Prospecting')], context=context)
        case_obj = pool.get('crm.case')
        case_obj._history(cr, uid, case_obj.browse(cr, uid, [data['id']]), 'convert')
        case_obj.write(cr, uid, data['ids'], {
            'section_id': id,
            'name': data['form']['name'],
            'planned_revenue': data['form']['planned_revenue'],
            'probability': data['form']['probability'],
            'stage_id' : stage_ids and stage_ids[0] or False,
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
