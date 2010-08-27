# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import tools
import pooler
from osv import osv, fields

class base_language_install(osv.osv_memory):
    """ Install Language"""

    _name = "base.language.install"
    _description = "Install Language"

    _columns = {
        'lang': fields.selection(tools.scan_languages(),'Language'),
    }

    def lang_install(self, cr, uid, ids, context):
        language_obj = self.browse(cr, uid, ids)[0]
        lang = language_obj.lang
        if lang:
            modobj = self.pool.get('ir.module.module')
            mids = modobj.search(cr, uid, [('state', '=', 'installed')])
            modobj.update_translations(cr, uid, mids, lang)

        data_obj = self.pool.get('ir.model.data')
        id2 = data_obj._get_id(cr, uid, 'base', 'view_base_language_install_msg')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'base.module.import.msg',
            'views': [(id2, 'form')],
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

base_language_install()

class base_language_install_msg(osv.osv_memory):
    """ Install Language"""

    _name = "base.language.install.msg"
    _description = "Install Language"

base_language_install_msg()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

