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


from openerp.osv import orm
import openerp

class res_lang(orm.Model):
    _inherit = 'res.lang'

    @openerp.tools.ormcache(skiparg=3)
    def _get_languages_dir(self, cr, uid, id, context=None):
        ids = self.search(cr, uid, [('active', '=', True)], context=context)
        langs = self.browse(cr, uid, ids, context=context)
        return dict([(lg.code, lg.direction) for lg in langs])

    def get_languages_dir(self, cr, uid, ids, context=None):
        return self._get_languages_dir(cr, uid, ids)

    def write(self, cr, uid, ids, vals, context=None):
        self._get_languages_dir.clear_cache(self)
        return super(res_lang, self).write(cr, uid, ids, vals, context)
