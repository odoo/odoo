# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com) 
# All Right Reserved
#
# Author : Vincent Renaville
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
import pooler
import ir
from tools.translate import _

class report_actions_wizard(wizard.interface):
    '''
    Add Print Buttons
    '''
    form = '''<?xml version="1.0"?>
    <form string="Add Print Buttons">
        <field name="print_button"/>
        <field name="open_action"/>
    </form>'''

    ex_form = '''<?xml version="1.0"?>
    <form string="Add Print Buttons">
        <label string="Report Action already exist for this report."/>
    </form>'''

    fields = {
        'print_button': 
                        {
                            'string': 'Add print button', 
                            'type': 'boolean', 
                            'default': True, 
                            'help':'Add action to menu context in print button.'
                        },
        'open_action': 
                        {
                            'string': 'Open added action',
                            'type': 'boolean', 
                            'default': False
                        },
    }

    def _do_action(self, cursor, uid, data, context):
        """Called in wizard init"""
        pool = pooler.get_pool(cursor.dbname)
        report = pool.get(data['model']).browse(
                                                cursor, 
                                                uid, 
                                                data['id'], 
                                                context=context
                                            )
        if data['form']['print_button']:
            res = ir.ir_set(
                            cursor, 
                            uid, 
                            'action', 
                            'client_print_multi',
                             report.report_name, 
                             [report.model], 
                             'ir.actions.report.xml,%d' % data['id'], 
                             isobject=True
                            )
        else:
            res = ir.ir_set(
                                cursor, 
                                uid, 
                                'action', 
                                'client_print_multi', 
                                report.report_name, 
                                [report.model,0], 
                                'ir.actions.report.xml,%d' % data['id'], 
                                isobject=True
                            )
        return {'value_id':res[0]}

    def _check(self, cursor, uid, data, context):
        """Check if button exist"""
        pool = pooler.get_pool(cursor.dbname)
        report = pool.get(data['model']).browse(
                                                    cursor, 
                                                    uid, 
                                                    data['id'], 
                                                    context=context
                                                )
        ids = pool.get('ir.values').search(
                            cursor, 
                            uid, 
                            [('value','=',report.type+','+str(data['id']))]
                        )
        if not ids:
            return 'add'
        else:
            return 'exist'

    def _action_open_window(self, cursor, uid, data, context):
        """Open a windows in client"""
        form=data['form']
        if not form['open_action']:
            return {}
        return {
            'domain':"[('id','=',%d)]" % (form['value_id']),
            'name': _('Client Actions Connections'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'ir.values',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
    
    states = {
        'init': {
            'actions': [],
            'result': {
                        'type':'choice',
                        'next_state':_check
                      }
        },
        'add': {
            'actions': [],
            'result': {
                        'type': 'form', 
                        'arch': form, 
                        'fields': fields, 
                        'state': (('end', '_Cancel'), ('process', '_Ok'))
                       },
        },
        'exist': {
            'actions': [],
            'result': {
                        'type': 'form', 
                        'arch': ex_form, 
                        'fields': {}, 
                        'state': (('end', '_Close'),)
                       },
        },
        'process': {
            'actions': [_do_action],
            'result': {
                        'type': 'state', 
                        'state': 'exit'
                       },
        },
        'exit': {
            'actions': [],
            'result': {
                        'type': 'action', 
                        'action': _action_open_window, 
                        'state': 'end'
                       },
        },
    }
report_actions_wizard('ir.report_actions')