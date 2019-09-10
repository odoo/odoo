# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import cStringIO

from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _

class base_update_translations(osv.osv_memory):
    def _get_languages(self, cr, uid, context):
        lang_obj = self.pool.get('res.lang')
        ids = lang_obj.search(cr, uid, ['&', ('active', '=', True), ('translatable', '=', True),])
        langs = lang_obj.browse(cr, uid, ids)
        return [(lang.code, lang.name) for lang in langs]

    def _get_lang_name(self, cr, uid, lang_code):
        lang_obj = self.pool.get('res.lang')
        ids = lang_obj.search(cr, uid, [('code', '=', lang_code)])
        if not ids:
            raise osv.except_osv(_('Error!'), _('No language with code "%s" exists') % lang_code)
        lang = lang_obj.browse(cr, uid, ids[0])
        return lang.name

    def act_update(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids)[0]
        lang_name = self._get_lang_name(cr, uid, this.lang)
        buf = cStringIO.StringIO()
        tools.trans_export(this.lang, ['all'], buf, 'csv', cr)
        tools.trans_load_data(cr, buf, 'csv', this.lang, lang_name=lang_name)
        buf.close()
        return {'type': 'ir.actions.act_window_close'}

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(base_update_translations, self).default_get(cr, uid, fields, context=context)
        
        if context.get('active_model') != "res.lang":
            return res
        
        record_id = context.get('active_id', False) or False
        if record_id:
            lang = self.pool.get('res.lang').browse(cr, uid, record_id).code
            res.update(lang=lang)
        return res

    _name = 'base.update.translations'
    _columns = {
        'lang': fields.selection(_get_languages, 'Language', required=True),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
