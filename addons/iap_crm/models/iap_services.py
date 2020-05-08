# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IapServices(models.AbstractModel):
    _inherit = 'iap.services'

    # ------------------------------------------------------------
    # CRM HELPERS AND TOOLS
    # ------------------------------------------------------------

    @api.model
    def _iap_get_lead_vals_from_clearbit_data(self, company_data, people_data, **additional_values):
        country_id = self.env['res.country'].search([('code', '=', company_data['country_code'])]).id
        state = self.env['res.country.state'].search([('code', '=', company_data['state_code']), ('country_id', '=', country_id)])
        state_id = state.id if state else False
        website_url = 'https://www.%s' % company_data['domain'] if company_data['domain'] else False
        lead_values = {
            'reveal_id': company_data['clearbit_id'],
            'name': company_data['name'] or company_data['domain'],
            'partner_name': company_data['legal_name'] or company_data['name'],
            'email_from': next(iter(company_data.get('email', [])), ''),
            'phone': company_data['phone'] or (company_data['phone_numbers'] and company_data['phone_numbers'][0]) or '',
            'website': website_url,
            'street': company_data['location'],
            'city': company_data['city'],
            'zip': company_data['postal_code'],
            'country_id': country_id,
            'state_id': state_id,
        }

        # If type is people then add first contact in lead data
        if people_data:
            lead_values.update({
                'contact_name': people_data[0]['full_name'],
                'email_from': people_data[0]['email'],
                'function': people_data[0]['title'],
            })

        if additional_values:
            lead_values.udpate(**additional_values)
        return lead_values
