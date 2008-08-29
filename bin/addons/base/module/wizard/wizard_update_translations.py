# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import osv, fields
import tools
import pooler
import StringIO

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
        buf=StringIO.StringIO()
        tools.trans_export(this.lang, ['all'], buf, 'csv', dbname=cr.dbname)
        tools.trans_load_data(cr.dbname, buf, 'csv', this.lang, lang_name=lang_name)
        buf.close()
        return {'type': 'ir.actions.act_window_close'}

    _name = 'wizard.module.update_translations'
    _columns = {
        'lang': fields.selection(_get_languages, 'Language', required=True),
    }

update_translations()
