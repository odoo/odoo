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

import time
import wizard
import osv
import pooler

section_form = '''<?xml version="1.0"?>
<form string="Create Menu">
    <separator string="Menu Information" colspan="4"/>
    <field name="menu_name"/>
    <field name="menu_parent_id"/>
    <field name="page" colspan="4"/>
</form>'''

section_fields = {
    'menu_name': {'string':'Menu Name', 'type':'char', 'required':True, 'size':64},
    'menu_parent_id': {'string':'Parent Menu', 'type':'many2one', 'relation':'ir.ui.menu', 'required':True},
    'page': {'string':'Group Home Page', 'type':'many2one', 'relation':'wiki.wiki'},
}

def wiki_menu_create(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    group = pool.get('wiki.groups').browse(cr, uid, data['id'])
    action_id = pool.get('ir.actions.wizard').search(cr, uid, [('wiz_name','=','wiki.wiki.page.open')])

    menu_id = pool.get('ir.ui.menu').create(cr, uid, {
        'name': data['form']['menu_name'],
        'parent_id': data['form']['menu_parent_id'],
        'icon': 'STOCK_DIALOG_QUESTION',
        'action': 'ir.actions.wizard,'+str(action_id[0])
    }, context)
    
    home = data['form']['page']
    group_id = data['id']
    res = {
        'home':home,
    }
    pool.get('wiki.groups').write(cr, uid, [data['id']], res)
    pool.get('wiki.groups.link').create(cr, uid, {'group_id':group_id, 'action_id':menu_id})
    
    return {}

class wizard_create_menu(wizard.interface):
    states = {
        'init': {
            'actions': [], 
            'result': {'type':'form', 'arch':section_form, 'fields':section_fields, 'state':[('end','Cancel'),('create_menu','Create Menu')]}
        },
        'create_menu': {
            'actions': [wiki_menu_create], 
            'result': {
                'type':'state', 
                'state':'end'
            }
        }
    }
wizard_create_menu('wiki.create.menu')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
