# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 OpenERP s.a. (<http://openerp.com>).
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

from openerp.controllers import SecuredController
from openerp.utils import rpc
from openobject.tools import expose
import cherrypy

class Root(SecuredController):

    _cp_path = "/openerp"

    @expose(mark_only=True)
    def menu(self, active=None, next=None):
        try:
            menu_id = int(active)
        except (TypeError, ValueError):
            menu_id = False

        menus = rpc.RPCProxy("ir.ui.menu")
        ids = menus.search([('parent_id', '=', False)])
        if next or active:
            if not menu_id and ids:
                menu_id = ids[0]

        menu = ''
        if menu_id:
            ctx = dict(lang='NO_LANG')  # force loading original string even if the english have been translated...
            menu = menus.read([menu_id], ['name'], ctx)[0]['name'] or ''

        general_forum = 77459
        forum = {
            'accounting': 87921,
            'administration': 87935,
            'human resources': 87923,
            'knowledge': 87927,
            'manufacturing': 87915,
            'marketing': 87925,
            'point of sale': 87929,
            'project': 87919,
            'purchases': 87911,
            'sales': 87907,
            'tools': 87933,
            'warehouse': 87913,
        }.get(menu.lower().strip(), general_forum)

        cherrypy.request.uservoice_forum = forum
        return super(Root, self).menu(active, next)


