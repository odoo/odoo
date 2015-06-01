# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
