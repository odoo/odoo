# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
import netsvc
import pooler

class wizard_update_module(wizard.interface):

    arch = '''<?xml version="1.0"?>
    <form string="Scan for new modules">
        <label string="This function will check for new modules in the 'addons' path and on module repositories:" colspan="4" align="0.0"/>
        <field name="repositories" colspan="4" nolabel="1"/>
    </form>'''
    fields = {
        'repositories': {'type': 'text', 'string': 'Repositories', 'readonly': True},
    }

    arch_module = '''<?xml version="1.0"?>
    <form string="New modules">
        <field name="update" colspan="4"/>
        <field name="add" colspan="4"/>
    </form>'''

    fields_module = {
        'update': {'type': 'integer', 'string': 'Number of modules updated', 'readonly': True},
        'add': {'type': 'integer', 'string': 'Number of modules added', 'readonly': True},
    }

    def _update_module(self, cr, uid, data, context):
        update, add = pooler.get_pool(cr.dbname).get('ir.module.module').update_list(cr, uid)
        return {'update': update, 'add': add}

    def _action_module_open(self, cr, uid, data, context):
        return {
            'domain': str([]),
            'name': 'Module List',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'ir.module.module',
            'view_id': False,
            'type': 'ir.actions.act_window'
        }

    def _get_repositories(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        repository_obj = pool.get('ir.module.repository')
        ids = repository_obj.search(cr, uid, [])
        res = repository_obj.read(cr, uid, ids, ['name', 'url'], context)
        return {'repositories': '\n'.join(map(lambda x: x['name']+': '+x['url'], res))}

    states = {
        'init': {
            'actions': [_get_repositories],
            'result': {'type': 'form', 'arch': arch, 'fields': fields,
                'state': [
                    ('end', 'Cancel', 'gtk-cancel'),
                    ('update', 'Check new modules', 'gtk-ok', True)
                ]
            }
        },
        'update': {
            'actions': [_update_module],
            'result': {'type': 'form', 'arch': arch_module, 'fields': fields_module,
                'state': [
                    ('open_window', 'Ok', 'gtk-ok', True)
                ]
            }
        },
        'open_window': {
            'actions': [],
            'result': {'type': 'action', 'action': _action_module_open, 'state':'end'}
        }
    }
wizard_update_module('module.module.update')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

