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
import pooler

def _get_default(obj, cursor, uid, data, context=None):
    '''Get default value'''
    return {'user': uid}

def _make_case(obj, cursor, uid, data, context=None):
    '''Create case'''
    pool = pooler.get_pool(cursor.dbname)
    case_obj = pool.get('crm.case')
    mod_obj = pool.get('ir.model.data')
    act_obj = pool.get('ir.actions.act_window')

    new_id = []

    for partner_id in data['ids']:
        new_id.append(case_obj.create(cursor, uid, {
            'name': data['form']['name'],
            'section_id': data['form']['section'],
            'partner_id': partner_id,
            'description': data['form']['description'],
            'user_id': data['form']['user'] or uid
            }))

    result = mod_obj._get_id(cursor, uid, 'crm', 'crm_case_categ0-act')
    res_id = mod_obj.read(cursor, uid, [result], ['res_id'])[0]['res_id']
    result = act_obj.read(cursor, uid, [res_id])[0]
    result['domain'] = str([('id', 'in', new_id)])
    return result


class MakeCase(wizard.interface):
    '''Wizard that create case on partner'''

    case_form = """<?xml version="1.0"?>
<form string="Make Case">
    <field name="name"/>
    <field name="section"/>
    <field name="user"/>
    <field name="description" colspan="4"/>
</form>"""

    case_fields = {
        'name': {'string': 'Case Description', 'type': 'char', 'size': 64,
            'required': True},
        'section': {'string': 'Case Section', 'type': 'many2one',
            'relation': 'crm.case.section', 'required': True},
        'user': {'string': 'User Responsible', 'type': 'many2one',
            'relation': 'res.users'},
        'description': {'string': 'Your action', 'type': 'text'},
    }

    states = {
        'init': {
            'actions': [_get_default],
            'result': {'type': 'form', 'arch': case_form, 'fields': case_fields,
                'state': [
                    ('end', 'Cancel'),
                    ('create', 'Create')
                ]
            }
        },
        'create': {
            'actions': [],
            'result': {'type': 'action', 'action': _make_case, 'state': 'end'}
        }
    }

MakeCase('sale_crm.make_case')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

