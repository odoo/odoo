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
from openerp.http import request

import lxml.html
import time
import logging


class Report(orm.Model):

    _inherit = 'report'

    def render(self, cr, uid, ids, template, values=None, context=None):
        if values is None:
            values = {}

        if context is None:
            context = {}
        langs = self.pool.get('res.lang').get_languages_dir(cr, uid, [], context=context)
        values['web_lang_dir'] = langs.get(context.get('lang', 'en_US'), 'ltr')

        view_obj = self.pool['ir.ui.view']

        def translate_doc(doc_id, model, lang_field, template):
            ctx = context.copy()
            doc = self.pool[model].browse(cr, uid, doc_id, context=ctx)
            qcontext = values.copy()
            # Do not force-translate if we chose to display the report in a specific lang
            if ctx.get('translatable') is True:
                qcontext['o'] = doc
            else:
                # Reach the lang we want to translate the doc into
                ctx['lang'] = eval('doc.%s' % lang_field, {'doc': doc})
                qcontext['o'] = self.pool[model].browse(cr, uid, doc_id, context=ctx)
                qcontext['web_lang_dir'] = langs.get(ctx['lang'], 'ltr')
                context['lang'] = ctx['lang']
            return view_obj.render(cr, uid, template, qcontext, context=ctx)

        user = self.pool['res.users'].browse(cr, uid, uid)
        website = None
        if request and hasattr(request, 'website'):
            website = request.website
        values.update(
            time=time,
            translate_doc=translate_doc,
            editable=True,  # Will active inherit_branding
            user=user,
            res_company=user.company_id,
            website=website,
            editable_no_editor=True,
        )
        return view_obj.render(cr, uid, template, values, context=context)

