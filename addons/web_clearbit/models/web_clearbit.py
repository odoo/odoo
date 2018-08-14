# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import clearbit
import logging
from odoo import api, fields, models, exceptions, _
from odoo.http import request
from requests.exceptions import ConnectionError, HTTPError

_logger = logging.getLogger(__name__)

class WebClearbit(models.AbstractModel):
    _name = 'web.clearbit'

    def _clearbit_set_key(self):
        clearbit.key = request.env['ir.config_parameter'].sudo().get_param('clearbit.api_key')
        if not clearbit.key:
            clearbit.key = request.env['ir.config_parameter'].sudo().get_param('clearbit.default_api_key')

        return clearbit.key

    @api.model
    def clearbit_enrich_company(self, company_domain):
        """
        Process the enrichment request.
        This function retrieve company informations with company domain
        See this page for received data format : https://clearbit.com/docs?python#enrichment-api-company-api
        """
        enrichment_data = {}

        if len(company_domain) > 0:
            if self._clearbit_set_key():
                try:
                    enrichment_data = clearbit.Company.find(domain=company_domain)
                    enrichment_data = dict(enrichment_data)
                    enrichment_data = self._format_data_company(enrichment_data)
                except (ConnectionError, HTTPError) as exception:
                    _logger.error('Clearbit Encrichment Connection failed: %s' % str(exception))
                    raise exceptions.UserError(_('Connection to Clearbit API failed. Please check your API key.'))

            else:
                _logger.error('No valid Clearbit API key found.')
                raise exceptions.UserError(_('No valid Clearbit API key found.'))

        return enrichment_data

    @api.model
    def clearbit_enrich_person(self, email):
        """
        Process the enrichment request.
        This function retrieve company and person informations with email
        See this page for received data format : https://clearbit.com/docs?python#enrichment-api-combined-api
        """
        enrichment_data = {
            'company': {},
            'person': {},
        }

        if len(email) > 0:
            self._clearbit_set_key()

            try:
                result = clearbit.Enrichment.find(email=email)
                result = dict(result)
                enrichment_data['company'] = self._format_data_company(result.company)
                enrichment_data['person'] = self._format_data_person(result.person)

            except (ConnectionError, HTTPError) as exception:
                _logger.error('Clearbit Encrichment Connection failed: %s' % str(exception))

        return enrichment_data

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

    def _format_data_person(self, person_data):
        return person_data

    def _find_country_data(self, state_code, state_name, country_code, country_name):
        result = {
            'country_id': False,
            'state_id': False
        }

        country_id = self.env['res.country'].search([['code', '=ilike', country_code]])
        if not country_id:
            country_id = self.env['res.country'].search([['name', '=ilike', country_name]])

        if country_id:
            result['country_id'] = {
                'id': country_id.id,
                'display_name': country_id.display_name
            }
            state_id = self.env['res.country.state'].search(
                [['country_id', '=', country_id.id], ['code', '=ilike', state_code]])
            if not state_id:
                state_id = self.env['res.country.state'].search(
                    [['country_id', '=', country_id.id], ['name', '=ilike', state_name]])

            if state_id:
                result['state_id'] = {
                    'id': state_id.id,
                    'display_name': state_id.display_name
                }

        else:
            _logger.info('Country code not found: %s', country_code)

        return result
