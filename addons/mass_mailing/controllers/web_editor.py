# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.web_editor.controllers.main import Web_Editor


class Web_Editor(Web_Editor):

    @http.route(["/website_mass_mailing/field/popup_content"], type='http', auth="user")
    def mass_mailing_FieldTextHtmlPopupTemplate(self, model=None, res_id=None, field=None, callback=None, **kwargs):
        kwargs['snippets'] = '/website/snippets'
        kwargs['template'] = 'mass_mailing.FieldTextHtmlPopupContent'
        return self.FieldTextHtml(model, res_id, field, callback, **kwargs)

    @http.route('/mass_mailing/field/email_template', type='http', auth="user")
    def mass_mailing_FieldTextHtmlEmailTemplate(self, model=None, res_id=None, field=None, callback=None, **kwargs):
        kwargs['snippets'] = '/mass_mailing/snippets'
        kwargs['template'] = 'mass_mailing.FieldTextHtmlInline'
        return self.FieldTextHtmlInline(model, res_id, field, callback, **kwargs)

    @http.route(['/mass_mailing/snippets'], type='json', auth="user", website=True)
    def mass_mailing_snippets(self):
        values = {'company_id': request.env['res.users'].browse(request.uid).company_id}
        return request.env.ref('mass_mailing.email_designer_snippets').render(values)
