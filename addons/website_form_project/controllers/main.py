# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.website_form.controllers.main import WebsiteForm


class WebsiteForm(WebsiteForm):

    @http.route('/website_form/<string:model_name>', type='http', auth='public', methods=['POST'], website=True)
    def website_form(self, model_name, **kwargs):
        """
            This method is responsible to set proper customer in created task.
            Issues is, Even if user submit form with email address, it will still set default customer from related project.
        """
        if model_name == 'project.task' and not request.params.get('partner_id') and request.params.get('email_from'):
            request.params['partner_id'] = False
            # If already partner of that email exist then set it as partner
            Partner = request.env['res.partner'].sudo().search([('email', '=', kwargs.get('email_from'))], limit=1)
            if Partner:
                request.params['partner_id'] = Partner.id
        return super(WebsiteForm, self).website_form(model_name, **kwargs)
