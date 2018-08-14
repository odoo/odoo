# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, fields, models, exceptions, _
from odoo.http import request
from requests.exceptions import ConnectionError, HTTPError

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    @api.model
    def enrich_company(self, company_domain):
        enrichment_data = {}
        return self._format_data_company(enrichment_data)


    def _format_data_company(self, company_data):
        lang_code = self._context.get('lang') or 'en_US'
        lang = self.env['res.lang']._lang_get(lang_code)

        geo_data = company_data['geo']
        site_data = company_data['site']
        metrics_data = company_data['metrics']
        category_data = company_data['category']
        phones = site_data['phoneNumbers']
        emails = site_data['emailAddresses']

        country_data = self._find_country_data(
            state_code=geo_data.get('stateCode', False),
            state_name=geo_data.get('state', False),
            country_code=geo_data.get('countryCode', False),
            country_name=geo_data.get('country', False)
        )

        phone = company_data.get('phone')
        if not phone and len(phones) > 0:
            phone = phones[0]

        email = False
        if len(emails) > 0:
            email = emails[0]

        comment = _("""
Description: 
%s

Founded year : %s
Employees : %s
Annual revenue : %s
Estimated annual revenue : %s

Sector : %s
Industry : %s > %s > %s 
Tags : %s 
            
Social networks :
www.facebook.com/%s
www.linkedin.com/%s
www.crunchbase.com/%s

Domain alias :
%s

Email addresses :
%s

Phone numbers :
%s
        """) % (company_data.get('description'),
                company_data.get('foundedYear') if company_data.get('foundedYear') else _('Unknown'),
                lang.format('%.0f', metrics_data.get('employees'), True, True) if metrics_data.get('employees') else _('Unknown'),
                '$%s' % lang.format('%.0f', metrics_data.get('annualRevenue'), True, True) if metrics_data.get('annualRevenue') else _('Unknown'),
                metrics_data.get('estimatedAnnualRevenue') if metrics_data.get('estimatedAnnualRevenue') else _('Unknown'),
                category_data.get('sector'),
                category_data.get('industryGroup'),
                category_data.get('industry'),
                category_data.get('subIndustry'),
                ' / '.join(company_data['tags']),
                company_data['facebook'].get('handle'),
                company_data['linkedin'].get('handle'),
                company_data['crunchbase'].get('handle'),
                ' / '.join(company_data['domainAliases']) if company_data['domainAliases'] else _('None'),
                ' / '.join(emails) if emails else _('None'),
                ' / '.join(phones) if phones else _('None'),
                )

        # if Extend addresses module is installed, try to find street number
        # if found, append it at the beginning of address
        if self.env['res.partner']._fields.get('street_number') and geo_data.get('streetNumber'):
            street = '%s %s' % (geo_data.get('streetNumber') or '', geo_data.get('streetName') or '')
        else:
            street = '%s %s' % (geo_data.get('streetName') or '', geo_data.get('streetNumber') or '')

        return {
            'country_id': country_data.get('country_id'),
            'state_id': country_data.get('state_id'),
            'website': company_data['domain'],
            'name': company_data.get('name'),
            'comment': comment,
            'street': street.strip(),
            'city': geo_data.get('city'),
            'zip': geo_data.get('postalCode'),
            'phone': phone,
            'email': email
        }

