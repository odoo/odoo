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

from osv import fields, osv

class wiki_create_menu(osv.osv_memory):
    """ Create Menu """
    _name = "wiki.create.menu"
    _description = "Wizard Create Menu"

    _columns = {
        'menu_name': fields.char('Menu Name', size=256, select=True, required=True),
        'menu_parent_id': fields.many2one('ir.ui.menu', 'Parent Menu', required=True),
    }

    def wiki_menu_create(self, cr, uid, ids, context=None):

        """ Create Menu On the base of Group id and Action id
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of create menu’s IDs

        """
        if context is None:
            context = {}
        obj_wiki_group = self.pool.get('wiki.groups')
        obj_view = self.pool.get('ir.ui.view')
        obj_menu = self.pool.get('ir.ui.menu')
        obj_action = self.pool.get('ir.actions.act_window')
        group_id = context.get('active_id', False)
        if not group_id:
            return {}

        datas = self.browse(cr, uid, ids, context=context)
        data = False
        if datas:
            data = datas[0]
        if not data:
            return {}
        value = {
            'name': 'Wiki Page',
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'wiki.wiki',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
        }
        group = obj_wiki_group.browse(cr, uid, group_id, context=context)
        value['domain'] = "[('group_id','=',%d)]" % (group.id)
        if group.method == 'page':
            value['res_id'] = group.home.id
        elif group.method == 'list':
            value['view_type'] = 'form'
            value['view_mode'] = 'tree,form'
        elif group.method == 'tree':
            view_id = obj_view.search(cr, uid, [('name', '=', 'wiki.wiki.tree.children')])
            value['view_id'] = view_id and view_id[0] or False
            value['domain'] = [('group_id', '=', group.id), ('parent_id', '=', False)]
            value['view_type'] = 'tree'

        action_id = obj_action.create(cr, uid, value)

        menu_id = obj_menu.create(cr, uid, {
                        'name': data.menu_name,
                        'parent_id':data.menu_parent_id.id,
                        'icon': 'STOCK_DIALOG_QUESTION',
                        'action': 'ir.actions.act_window,'+ str(action_id),
                        }, context)
        obj_wiki_group.write(cr, uid, [group_id], {'menu_id':menu_id})
        return {'type':  'ir.actions.act_window_close'}


wiki_create_menu()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
