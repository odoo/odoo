# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from urllib.parse import urlparse

from odoo import fields, models, tools, _


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    partner_gid = fields.Integer('Company database ID', related="partner_id.partner_gid", inverse="_inverse_partner_gid", store=True)

    def _inverse_partner_gid(self):
        for company in self:
            company.partner_id.partner_gid = company.partner_gid

    def _enrich(self):
        """
        This method calls the partner autocomplete service from IAP to enrich the partner related fields
        of the company.
        """
        self.ensure_one()

        company_domain = self._get_company_domain()
        if not company_domain:
            return {'error': _("Could not extract company domain. Impossible to enrich the company.")}

        company_data = self.env['res.partner'].enrich_company(company_domain, False, self.vat)
        if company_data.get('error'):
            return {'error': company_data.get('error_message', _('Unkown reason'))}

        for field in ['state_id', 'country_id']:
            company_data[field] = company_data.get(field, {}).get('id')

        additional_data = company_data.pop('additional_info', False)

        # Keep only truthy values that are not already set on the target partner
        company_data = {field: value for field, value in company_data.items()
                        if field in self.partner_id._fields and value and not self.partner_id[field]}

        self.partner_id.write(company_data)
        if additional_data:
            template_values = json.loads(additional_data)
            template_values['flavor_text'] = _("Company auto-completed by Odoo Partner Autocomplete Service")
            self.partner_id.message_post_with_view(
                'iap_mail.enrich_company',
                values=template_values,
                subtype_id=self.env.ref('mail.mt_note').id,
            )
        return {}

    def _get_company_domain(self):
        """ Extract the company domain to be used by IAP services.
        The domain is extracted from the website or the email information.
        e.g:
            - www.info.proximus.be -> proximus.be
            - info@proximus.be -> proximus.be """
        self.ensure_one()

        if self.website:
            company_domain = urlparse(self.website).netloc
            if '.' in company_domain:
                return '.'.join(company_domain.split('.')[-2:])  # remove subdomains

        if self.email:
            normalized_email = tools.email_normalize(self.email)
            if normalized_email:
                return normalized_email.split('@')[1]

        return False
