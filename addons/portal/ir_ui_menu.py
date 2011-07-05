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

import logging

from osv import osv, fields
from tools.safe_eval import safe_eval

class portal_menu(osv.osv):
    """
        Fix menu class to customize the login search for menus,
        as web client 6.0 does not support the menu action properly yet
    """
    _name = 'ir.ui.menu'
    _inherit = 'ir.ui.menu'

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        
        # if the user belongs to a portal, we have to rewrite any search on the
        # top menus to be under the portal's parent menu
        if not context.get('ir.ui.menu.full_list') and uid != 1 and \
                args == [('parent_id', '=', False)]:
            portal_obj = self.pool.get('res.portal')
            portal_ids = portal_obj.search(cr, uid, [('users', 'in', uid)])
            if portal_ids:
                if len(portal_ids) > 1:
                    log = logging.getLogger('ir.ui.menu')
                    log.warning('User %s belongs to several portals', str(uid))
                p = portal_obj.browse(cr, uid, portal_ids[0])
                # if the portal overrides the menu, use its domain
                if p.menu_action_id:
                    args = safe_eval(p.menu_action_id.domain)
        
        return super(portal_menu, self).search(cr, uid, args, offset=offset,
                    limit=limit, order=order, context=context, count=count)

portal_menu()

