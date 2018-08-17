# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, fields, models, exceptions, _
from odoo.http import request
from odoo.addons.iap import jsonrpc
from requests.exceptions import ConnectionError, HTTPError
import requests

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    company_data_id = fields.Integer('Company database ID')

    @api.model
    def enrich_company(self, company_domain):
        enrichment_data = False

        try:
            # make HTTP request to IAP service /

            # TODO: Use IAP.jsonrpc instead

            url = 'http://odoo:8069/iap/partner_autocomplete/domain'
            params = {
                'domain': company_domain,
                'country_code': self.env.user.company_id.country_id.code,
            }

            enrichment_data = jsonrpc(url, params=params)

        #     payload = {
        #         'jsonrpc': '2.0',
        #         'id': None,
        #         'method': 'call',
        #         'params': {
        #             'domain': company_domain,
        #             'country_code': self.env.user.company_id.country_id.code,
        #         }
        #     }
        #     req = requests.post(url, json=payload)
        #     req.raise_for_status()
        #     response = req.json()
        #     if 'error' in response:
        #         name = response['error']['data'].get('name').rpartition('.')[-1]
        #         message = response['error']['data'].get('message')
        #         if name == 'AccessError':
        #             e_class = exceptions.AccessError
        #         elif name == 'UserError':
        #             e_class = exceptions.UserError
        #         else:
        #             raise requests.exceptions.ConnectionError()
        #         e = e_class(message)
        #         e.data = response['error']['data']
        #         raise e
        #     else:
        #         enrichment_data = response.get('result')

        except (ConnectionError, HTTPError, exceptions.AccessError ) as exception:
            _logger.error('Enrichment API error: %s' % str(exception))
            raise exceptions.UserError(_('Connection to Encrichment API failed.'))

        return self._format_data_company(enrichment_data)

    @api.model
    def _format_data_company(self, company_data):
        lang_code = self._context.get('lang') or 'en_US'
        lang = self.env['res.lang']._lang_get(lang_code)

        country_data = self._find_country_data(
            state_code=company_data.get('state_code', False),
            state_name=company_data.get('state_name', False),
            country_code=company_data.get('country_code', False),
            country_name=company_data.get('country_name', False)
        )

        phones = company_data['phone_numbers']
        emails = company_data['email']

        phone = company_data.get('phone')
        if not phone and len(phones) > 0:
            phone = phones.pop(0)

        email = False
        if len(emails) > 0:
            email = emails.pop(0)

        comment = _("""
            Description: 
            %s

            Employees : %s
            Annual revenue : %s
            Estimated annual revenue : %s

            Sector : 
            %s

            Tech : 
            %s

            Social networks :
            www.facebook.com/%s
            www.linkedin.com/%s
            www.crunchbase.com/%s
            www.twitter.com/%s

            Email addresses :
            %s

            Phone numbers :
            %s
            """) % (company_data.get('description'),
            lang.format('%.0f', float(company_data.get('employees')), True, True) if company_data.get('employees') else _('Unknown'),
            '$%s' % lang.format('%.0f', float(company_data.get('annual_revenue')), True, True) if company_data.get('annual_revenue') else _('Unknown'),
            company_data.get('estimated_annual_revenue') if company_data.get('estimated_annual_revenue') else _('Unknown'),
            company_data.get('sector'),
            ' / '.join(company_data.get('tech')),
            company_data.get('facebook'),
            company_data.get('linkedin'),
            company_data.get('crunchbase'),
            company_data.get('twitter'),
            ' / '.join(emails) if emails else _('None'),
            ' / '.join(phones) if phones else _('None'),
        )

        company = {
            'country_id': country_data.get('country_id'),
            'state_id': country_data.get('state_id'),
            'website': company_data['domain'],
            'name': company_data.get('name'),
            'comment': comment,
            'city': company_data.get('city'),
            'zip': company_data.get('postal_code'),
            'phone': phone,
            'email': email,
            'company_data_id': company_data.get('company_data_id'),
        }

        street = self._split_street_with_params('%s %s' % (company_data.get('street_name'), company_data.get('street_number')), '%(street_name)s, %(street_number)s/%(street_number2)s')
        company.update(street)

        return company

    @api.model
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
            if state_name or state_code:
                state_id = self.env['res.country.state'].search([
                    ('country_id', '=', country_id.id),
                    '|',
                        ('name', '=ilike', state_name),
                        ('code', '=ilike', state_code)
                    ], limit=1)

                if state_id:
                    result['state_id'] = {
                        'id': state_id.id,
                        'display_name': state_id.display_name
                    }

        else:
            _logger.info('Country code not found: %s', country_code)

        return result


# ---- FROM BASE VAT AUTOCOMPLETE ----

    def _get_vies_company_data(self, vat):
        vies_vat_data = False

        try:
            # make HTTP request to IAP service /

            # TODO: Use IAP.jsonrpc instead

            url = 'http://odoo:8069/iap/partner_autocomplete/vat'
            params = {
                'domain': company_domain,
                'country_code': self.env.user.company_id.country_id.code,
            }

            vies_vat_data = jsonrpc(url, params=params)

        except (ConnectionError, HTTPError, exceptions.AccessError) as exception:
            _logger.error('Enrichment API error: %s' % str(exception))
            raise exceptions.UserError(_('Connection to Encrichment API failed.'))

        return vies_vat_data

    def _check_vat_format(self, search_val):
        return len(search_val) > 5 and search_val[:2].lower() in stdnum_vat.country_codes

    @api.model
    def vies_vat_search(self, search_val=""):
        if self._check_vat_format(search_val):
            return self._get_vies_company_data(search_val)
        return False

    @api.onchange('vat')
    def vies_vat_change(self):
        if stdnum_vat is None:
            return {}

        for partner in self:
            if not partner.vat:
                continue
            # If a field is not set in the response, wipe it anyway
            non_set_address_fields = self._get_all_address_fields()
            if self._check_vat_format(partner.vat):
                company_data = self._get_vies_company_data(partner.vat)

                if not partner.name and company_data['name']:
                    partner.name = company_data['name']

                #set the address fields
                for field, value in company_data.items():
                    if(field in non_set_address_fields):
                        partner[field] = value
                        non_set_address_fields.remove(field)
                for field in non_set_address_fields:
                    if partner[field]:
                        partner[field] = False


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.onchange('vat')
    def vies_vat_change(self):
        self.ensure_one()
        company_address_fields = ['street', 'street2', 'city', 'zip', 'state_id', 'country_id']
        company_data = self.env['res.partner']._get_vies_company_data(self.vat)
        if not self.name and company_data['name']:
            self.name = company_data['name']

        #set the address fields
        for field, value in company_data.items():
            if(field in company_address_fields):
                self[field] = value
                company_address_fields.remove(field)
        for field in company_address_fields:
            if self[field]:
                self[field] = False
