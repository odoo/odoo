# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlparse

import json
import base64
import logging
import requests

from odoo.addons.iap.tools import iap_tools
from odoo import fields, models, tools, _

_logger = logging.getLogger(__name__)

COMPANY_AC_TIMEOUT = 5


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

        company_data = self.env['res.partner'].enrich_company(company_domain, False, self.vat, timeout=COMPANY_AC_TIMEOUT)
        if company_data.get('error'):
            return {'error': company_data.get('error_message', _('Unkown reason'))}

        additional_data = company_data.pop('additional_info', False)

        if company_data.get('logo'):
            # Erase image_1920 even if something is in it. Indeed as partner_autocomplete is probably installed as a
            # core app (mail -> iap -> partner_autocomplete auto install chain) it is unlikely that people already
            # updated their company logo.
            try:
                company_data['image_1920'] = base64.b64encode(
                    requests.get(company_data['logo'], timeout=COMPANY_AC_TIMEOUT).content
                )
            except Exception as e:
                _logger.warning('Download of image for new company %r failed, error %r' % (self.name, e))

        # Keep only truthy values that are not already set on the target partner
        company_data = {field: value for field, value in company_data.items()
                        if field in self.partner_id._fields and field != 'image_1920' and value and not self.partner_id[field]}

        company_data = self._enrich_extract_ids(company_data, ['state_id', 'country_id'])
        if company_data.get('child_ids'):
            child_ids = []
            for child_data in company_data['child_ids']:
                child_ids.append(self._enrich_extract_ids(child_data, ['state_id', 'country_id']))
            company_data['child_ids'] = child_ids

        # handle o2m values. Returned in the form: E.g. {'child_ids': [{'name': 'Value 1'}, {'name': 'Value 2'}]}
        for o2m_field, create_values in company_data.items():
            if isinstance(create_values, list):
                commands = [(
                    0, 0, create_value
                ) for create_value in create_values if isinstance(create_value, dict)]

                if commands:
                    company_data[o2m_field] = commands
                else:
                    del company_data[o2m_field]

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

    def _enrich_extract_ids(self, data, fields):
        """ Extract country and state ids from data (because of res.partner._format_data_company)
         This method is called during _enrich company process and is used twice:
         For company_data itself and for child_ids """
        for field in fields:
            if isinstance(data.get(field), dict):
                data[field] = data.get(field).get('id')
        return data

    def _get_company_domain(self):
        """ Extract the company domain to be used by IAP services.
        The domain is extracted from the website or the email information.
        e.g:
            - www.info.proximus.be -> proximus.be
            - info@proximus.be -> proximus.be """
        self.ensure_one()

        company_domain = tools.email_domain_extract(self.email) if self.email else False
        if company_domain and company_domain not in iap_tools._MAIL_DOMAIN_BLACKLIST:
            return company_domain

        company_domain = tools.url_domain_extract(self.website) if self.website else False
        if not company_domain or company_domain in ['localhost', 'example.com']:
            return False

        return company_domain
