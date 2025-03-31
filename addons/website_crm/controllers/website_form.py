# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.website.controllers import form
from odoo.http import request


class WebsiteForm(form.WebsiteForm):

    def _get_country(self):
        visitor_partner = request.env['website.visitor']._get_visitor_from_request().partner_id
        if visitor_partner:
            # match same behaviour as in partner._phone_format()
            country = visitor_partner.country_id or request.env.company.country_id
            if country:
                return country
        country_code = request.geoip.country_code
        if country_code:
            return request.env['res.country'].sudo().search([('code', '=', country_code)], limit=1)
        return request.env['res.country']

    # Check and insert values from the form on the model <model> + validation phone fields
    def _handle_website_form(self, model_name, **kwargs):
        model_record = request.env['ir.model'].sudo().search([('model', '=', model_name), ('website_form_access', '=', True)])
        if model_record:
            try:
                data = self.extract_data(model_record, request.params)
            except:
                # no specific management, super will do it
                pass
            else:
                record = data.get('record', {})
                phone_fields = request.env[model_name]._phone_get_number_fields()
                country = request.env['res.country'].browse(record.get('country_id'))
                contact_country = country if country.exists() else self._get_country()
                for phone_field in phone_fields:
                    if not record.get(phone_field):
                        continue
                    number = record[phone_field]
                    fmt_number = phone_validation.phone_format(
                        number, contact_country.code if contact_country else None,
                        contact_country.phone_code if contact_country else None,
                        force_format='INTERNATIONAL',
                        raise_exception=False
                    )
                    request.params.update({phone_field: fmt_number})

        if model_name == 'crm.lead' and not request.params.get('state_id'):
            geoip_country_code = request.geoip.country_code
            geoip_state_code = request.geoip.subdivisions[0].iso_code if request.geoip.subdivisions else None
            if geoip_country_code and geoip_state_code:
                state = request.env['res.country.state'].search([('code', '=', geoip_state_code), ('country_id.code', '=', geoip_country_code)])
                if state:
                    request.params['state_id'] = state.id
        return super(WebsiteForm, self)._handle_website_form(model_name, **kwargs)

    def insert_record(self, request, model, values, custom, meta=None):
        is_lead_model = model.sudo().model == 'crm.lead'
        if is_lead_model:
            values_email_normalized = tools.email_normalize(values.get('email_from'))
            visitor_sudo = request.env['website.visitor']._get_visitor_from_request(force_create=True)
            visitor_partner = visitor_sudo.partner_id
            if values_email_normalized and visitor_partner and visitor_partner.email_normalized == values_email_normalized:
                # Here, 'phone' in values has already been formatted, see _handle_website_form.
                values_phone = values.get('phone')
                # We write partner id on crm only if no phone exists on partner or in input,
                # or if both numbers (after formating) are the same. This way we get additional phone
                # if possible, without modifying an existing one. (see inverse function on model crm.lead)
                if values_phone and visitor_partner.phone:
                    if values_phone == visitor_partner.phone:
                        values['partner_id'] = visitor_partner.id
                    elif (visitor_partner._phone_format('phone') or visitor_partner.phone) == values_phone:
                        values['partner_id'] = visitor_partner.id
                else:
                    values['partner_id'] = visitor_partner.id
            if 'company_id' not in values:
                values['company_id'] = request.website.company_id.id
            lang = request.context.get('lang', False)
            values['lang_id'] = values.get('lang_id') or request.env['res.lang']._get_data(code=lang).id

        result = super(WebsiteForm, self).insert_record(request, model, values, custom, meta=meta)

        if is_lead_model and visitor_sudo and result:
            lead_sudo = request.env['crm.lead'].browse(result).sudo()
            if lead_sudo.exists():
                vals = {'lead_ids': [(4, result)]}
                if not visitor_sudo.lead_ids and not visitor_sudo.partner_id:
                    vals['name'] = lead_sudo.contact_name
                visitor_sudo.write(vals)
        return result
