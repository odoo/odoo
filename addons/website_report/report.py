# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today OpenERP SA (<http://www.openerp.com>).
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

from openerp.addons.web.http import request
from openerp.osv import osv


class Report(osv.Model):
    _inherit = 'report'

    def translate_doc(self, cr, uid, doc_id, model, lang_field, template, values, context=None):
        if request and hasattr(request, 'website'):
            if request.website is not None:
                v = request.website.get_template(template)
                request.session['report_view_ids'].append({
                    'name': v.name,
                    'id': v.id,
                    'xml_id': v.xml_id,
                    'inherit_id': v.inherit_id.id,
                    'header': False,
                    'active': v.active,
                })
        return super(Report, self).translate_doc(cr, uid, doc_id, model, lang_field, template, values, context=context)

    def render(self, cr, uid, ids, template, values=None, context=None):
        if request and hasattr(request, 'website'):
            if request.website is not None:
                request.session['report_view_ids'] = []
        return super(Report, self).render(cr, uid, ids, template, values=values, context=context)
