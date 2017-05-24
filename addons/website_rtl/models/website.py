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


from openerp.osv import orm, fields
from openerp.http import request

import openerp


class Website(orm.Model):
    _inherit = 'website'

    @openerp.tools.ormcache(skiparg=3)
    def _get_languages_dir(self, cr, uid, id, context=None):
        website = self.browse(cr, uid, id)
        return dict([(lg.code, lg.direction) for lg in website.language_ids])

    def get_languages_dir(self, cr, uid, ids, context=None):
        return self._get_languages_dir(cr, uid, ids[0])

    def write(self, cr, uid, ids, vals, context=None):
        self._get_languages_dir.clear_cache(self)
        return super(Website, self).write(cr, uid, ids, vals, context)
