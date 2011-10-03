# -*- coding: utf-8 -*-
#############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP SA (<http://openerp.com>).
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

import web.common.dispatch as openerpweb


class UserVoiceController(openerpweb.Controller):
    _cp_path = '/web_uservoice/uv'

    @openerpweb.jsonrequest
    def forum(self, req, menu_id):
        menu = ''
        if menu_id:
            try:
                menu_id = int(menu_id)
            except ValueError:
                pass
            else:
                ctx = dict(lang='NO_LANG')  # force loading original string even if the english have been translated...
                menus = req.session.model('ir.ui.menu')
                try:
                    menu = menus.read([menu_id], ['name'], ctx)[0]['name'] or ''
                except KeyError:
                    pass

        general_forum = '77459'
        forum = {
            'accounting': '87921',
            'administration': '87935',
            'human resources': '87923',
            'knowledge': '87927',
            'manufacturing': '87915',
            'marketing': '87925',
            'point of sale': '87929',
            'project': '87919',
            'purchases': '87911',
            'sales': '87907',
            'tools': '87933',
            'warehouse': '87913',
        }.get(menu.lower().strip(), general_forum)

        return {'forum': forum}

