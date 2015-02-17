# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models
from openerp.http import request


class Report(models.Model):
    _inherit = 'report'

    @api.v7
    def translate_doc(self, cr, uid, doc_id, model, lang_field, template, values, context=None):
        if request and hasattr(request, 'website'):
            if request.website:
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

    @api.v8
    def translate_doc(self, model, lang_field, template, values):
        return self._model.translate_doc(self._cr, self._uid, self.ids, model, lang_field, template, values, context=self._context)

    @api.multi
    def render(self, template, values=None):
        if request and hasattr(request, 'website'):
            if request.website:
                request.session['report_view_ids'] = []
        return super(Report, self).render(template, values=values)
