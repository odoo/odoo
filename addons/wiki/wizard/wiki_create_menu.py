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
        'page': fields.many2one('wiki.wiki', 'Group Home Page'),
    }

    def wiki_menu_create(self, cr, uid, ids, context):

        """ Create Menu On the base of Group id and Action id
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of create menu’s IDs

        """
        data = context and context.get('active_id', False) or False
        mod_obj = self.pool.get('ir.model.data')
        action_id = mod_obj._get_id(cr, uid, 'wiki', 'action_view_wiki_wiki_page_open')

        for menu in self.browse(cr, uid, ids):
            menu_id = self.pool.get('ir.ui.menu').create(cr, uid, {
                            'name': menu.menu_name,
                            'parent_id':menu.menu_parent_id.id,
                            'icon': 'STOCK_DIALOG_QUESTION',
                            'action': 'ir.actions.act_window,'+ str(action_id)[0]
                            }, context)
            home = menu.page.id
            group_id = data
            res = {
                    'home': home,
                    }
            self.pool.get('wiki.groups').write(cr, uid, ids, res)
            self.pool.get('wiki.groups.link').create(cr, uid,
                                {'group_id': group_id, 'action_id': menu_id})
        return {}

wiki_create_menu()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
