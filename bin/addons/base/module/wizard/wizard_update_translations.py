# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields
import tools
import pooler
import cStringIO

class update_translations(osv.osv_memory):
    def _get_languages(self, cr, uid, context):
        lang_obj=pooler.get_pool(cr.dbname).get('res.lang')
        ids=lang_obj.search(cr, uid, ['&', ('active', '=', True), ('translatable', '=', True),])
        langs=lang_obj.browse(cr, uid, ids)
        return [(lang.code, lang.name) for lang in langs]
   
    def _get_lang_name(self, cr, uid, lang_code):
        lang_obj=pooler.get_pool(cr.dbname).get('res.lang')
        ids=lang_obj.search(cr, uid, [('code', '=', lang_code)])
        if not ids:
            raise osv.orm_except('Bad lang')
        lang = lang_obj.browse(cr, uid, ids[0])
        return lang.name
    def act_cancel(self, cr, uid, ids, context=None):
        return {'type': 'ir.actions.act_window_close'}

    def act_update(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids)[0]
        lang_name = self._get_lang_name(cr, uid, this.lang)
        buf=cStringIO.StringIO()
        tools.trans_export(this.lang, ['all'], buf, 'csv', dbname=cr.dbname)
        tools.trans_load_data(cr.dbname, buf, 'csv', this.lang, lang_name=lang_name)
        buf.close()
        return {'type': 'ir.actions.act_window_close'}

    _name = 'wizard.module.update_translations'
    _columns = {
        'lang': fields.selection(_get_languages, 'Language', required=True),
    }

update_translations()
