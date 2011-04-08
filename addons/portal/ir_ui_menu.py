# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 OpenERP S.A (<http://www.openerp.com>).
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

from osv import osv, fields

class portal_menu(osv.osv):
    """Inherited menu class to customized the login search for menus,
       as web client 6.0 does not support the menu action properly yet"""

    _inherit = 'ir.ui.menu'

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        # if the current user belongs to a portal, we have to
        # rewrite any search on the top menus to be under the
        # portal's root menu:
        if not context.get('ir.ui.menu.full_list') and uid != 1 and \
                            args and len(args) == 1 and \
                            len(args[0]) == 3 and \
                            (args[0][0] == 'parent_id' \
                                and args[0][1] == '=' \
                                and args[0][2] == False):
                Portals = self.pool.get('res.portal')
                portal_id = Portals.search(cr, uid, [('group_id.users', 'in', uid)])
                if portal_id:
                    assert len(portal_id) == 1, "Users may only belong to one portal at a time!"
                    portal_data = Portals.read(cr, uid, portal_id[0], ['parent_menu_id'])
                    menu_id_pair = portal_data.get('parent_menu_id') # (ID, Name)
                    if menu_id_pair:
                        args = [('parent_id', '=', menu_id_pair[0])]
        ids = super(portal_menu, self).search(cr, uid, args, offset=0,
                        limit=None, order=order, context=context, count=False)
        return len(ids) if count else ids
portal_menu()