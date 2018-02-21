# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_form.controllers.main import WebsiteForm
from odoo.http import request, route


class WebsiteForm(WebsiteForm):

    def _get_country(self):
        country_code = request.session.geoip and request.session.geoip.get('country_code') or False
        if country_code:
            return request.env['res.country'].sudo().search([('code', '=', country_code)], limit=1)
        return request.env['res.country']

    def _get_phone_fields_to_validate(self):
        return ['phone', 'mobile']

    @route('/website_form/<string:model_name>', type='http', auth="public", methods=['POST'], website=True)
    def website_form(self, model_name, **kwargs):
        model_record = request.env['ir.model'].sudo().search([('model', '=', model_name), ('website_form_access', '=', True)])
        if not model_record or not hasattr(request.env[model_name], 'phone_format'):
            return super(WebsiteForm, self).website_form(model_name, **kwargs)

        try:
            data = self.extract_data(model_record, request.params)
        except:
            # no specific management, super will do it
            pass
        else:
            record = data.get('record', {})
            phone_fields = self._get_phone_fields_to_validate()
            country = request.env['res.country'].browse(record.get('country_id'))
            contact_country = country.exists() and country or self._get_country()
            for phone_field in phone_fields:
                if not record.get(phone_field):
                    continue
                number = record[phone_field]
                fmt_number = request.env[model_name].phone_format(number, contact_country)
                request.params.update({phone_field: fmt_number})

        return super(WebsiteForm, self).website_form(model_name, **kwargs)
