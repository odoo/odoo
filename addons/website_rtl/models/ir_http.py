# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo RTL support
#    Copyright (C) 2014 Mohammed Barsi.
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


from openerp.http import request
from openerp.osv import orm


class ir_http(orm.AbstractModel):
    _inherit = 'ir.http'

    def _dispatch(self):
        resp = super(ir_http, self)._dispatch()
        if request.website:
            langs = request.website.get_languages_dir()
            direction = langs.get(request.context['lang'], None)
            if direction is None:
                direction = 'ltr'
            request.context['website_lang_dir'] = direction 
        return resp
