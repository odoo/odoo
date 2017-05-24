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

class QWeb(orm.AbstractModel):
    """ QWeb object for rendering stuff in the website context
    """
    _inherit = 'website.qweb'

    def render(self, cr, uid, id_or_xml_id, qwebcontext=None, loader=None, context=None):
        if request.website:
            langs = request.website.get_languages_dir()
            direction = langs.get(request.context['lang'], None)
            if direction is None:
                direction = 'ltr'
        qwebcontext['website_lang_dir'] = direction
        return super(QWeb, self).render(cr, uid, id_or_xml_id, qwebcontext=qwebcontext, loader=loader, context=context)

