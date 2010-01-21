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
import time
import tools
import os

view_form_finish = '''<?xml version="1.0"?>
<form string="Setup">
    <image name="gtk-dialog-info" colspan="2"/>
    <group colspan="2" col="4">
        <separator colspan="4" string="Installation Done"/>
        <label align="0.0" colspan="4" string="Your new database is now fully installed."/>
        <label align="0.0" colspan="4" string="You can start configuring the system or connect directly to the database using the default setup."/>
    </group>
</form>
'''

class wizard_base_setup(wizard.interface):

    def _menu(self, cr, uid, data, context):
        users_obj=pooler.get_pool(cr.dbname).get('res.users')
        action_obj=pooler.get_pool(cr.dbname).get('ir.actions.act_window')

        ids=action_obj.search(cr, uid, [('name', '=', 'Menu')])
        menu=action_obj.browse(cr, uid, ids)[0]

        ids=users_obj.search(cr, uid, [('action_id', '=', 'Setup')])
        users_obj.write(cr, uid, ids, {'action_id': menu.id})
        ids=users_obj.search(cr, uid, [('menu_id', '=', 'Setup')])
        users_obj.write(cr, uid, ids, {'menu_id': menu.id})

        return {
            'name': menu.name,
            'type': menu.type,
            'view_id': (menu.view_id and\
                    (menu.view_id.id, menu.view_id.name)) or False,
            'domain': menu.domain,
            'res_model': menu.res_model,
            'src_model': menu.src_model,
            'view_type': menu.view_type,
            'view_mode': menu.view_mode,
            'views': menu.views,
        }

    def _config(self, cr, uid, data, context=None):
        pool = pooler.get_pool(cr.dbname)
        users_obj=pool.get('res.users')
        action_obj=pool.get('ir.actions.act_window')

        ids=action_obj.search(cr, uid, [('name', '=', 'Menu')])
        menu=action_obj.browse(cr, uid, ids)[0]

        ids=users_obj.search(cr, uid, [('action_id', '=', 'Setup')])
        users_obj.write(cr, uid, ids, {'action_id': menu.id})
        ids=users_obj.search(cr, uid, [('menu_id', '=', 'Setup')])
        users_obj.write(cr, uid, ids, {'menu_id': menu.id})

        return pool.get('res.config').next(cr, uid, [], context=context)

    states={
        'init':{
            'result': {'type': 'form', 'arch': view_form_finish, 'fields': {},
                'state': [
                    ('menu', 'Use Directly', 'gtk-ok'),
                    ('config', 'Start Configuration', 'gtk-go-forward', True)
                ]
            }
        },
        'config': {
            'result': {
                'type': 'action',
                'action': _config,
                'state': 'end',
            },
        },
        'menu': {
            'actions': [],
            'result': {'type': 'action', 'action': _menu, 'state': 'end'}
        },
    }

wizard_base_setup('base_setup.base_setup')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

