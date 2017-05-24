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
from openerp import SUPERUSER_ID

from openerp.http import request


class QWeb(orm.AbstractModel):
    _inherit = 'ir.qweb'

    def render(self, cr, uid, id_or_xml_id, qwebcontext=None, loader=None, context=None):
        context = context or {}
        if qwebcontext and qwebcontext.get('web_lang_dir', None):
            
            return super(QWeb, self).render(
                cr,
                uid,
                id_or_xml_id,
                qwebcontext=qwebcontext,
                loader=loader,
                context=context)
        lang_obj = self.pool.get('res.lang')
        lang = context.get('lang', None)
        if not lang:
            if qwebcontext.get('lang', None):
                lang = qwebcontext.get('lang')
            elif uid:
                user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
                lang = user.partner_id.lang
            else:
                lang = 'en_US'
        directions = lang_obj.get_languages_dir(cr, uid, [], context=context)
        direction = directions.get(lang, 'ltr')
        qwebcontext['web_lang_dir'] = qwebcontext.get('web_lang_dir', None) or direction
        
        return super(QWeb, self).render(
            cr,
            uid,
            id_or_xml_id,
            qwebcontext=qwebcontext,
            loader=loader,
            context=context)
