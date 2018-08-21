# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, fields, models, exceptions, _
from odoo.addons.iap import jsonrpc
from requests.exceptions import ConnectionError, HTTPError

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    company_data_id = fields.Integer('Company database ID')

    @api.model
    def autocomplete(self, query):
        enrichment_data = False

        try:
            url = 'http://odoo:8069/iap/partner_autocomplete/name'
            params = {
                'query': query,
                'country_code': self.env.user.company_id.country_id.code,
            }

            suggestions = jsonrpc(url, params=params)
            suggestions = self._format_data_company(suggestions)
        except (ConnectionError, HTTPError, exceptions.AccessError ) as exception:
            _logger.error('Autocomplete API error: %s' % str(exception))
            raise exceptions.UserError(_('Connection to Autocomplete API failed.'))

        return suggestions

    @api.model
    def enrich_company(self, company_domain, company_data_id):
        enrichment_data = False

        try:
            url = 'http://odoo:8069/iap/partner_autocomplete/domain'
            params = {
                'domain': company_domain,
                'company_data_id': company_data_id,
                'country_code': self.env.user.company_id.country_id.code,
            }

            enrichment_data = jsonrpc(url, params=params)
            enrichment_data = self._format_data_company(enrichment_data)
        except (ConnectionError, HTTPError, exceptions.AccessError ) as exception:
            _logger.error('Enrichment API error: %s' % str(exception))
            raise exceptions.UserError(_('Connection to Encrichment API failed.'))

        return enrichment_data

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

        comment = _("\
            Description: \n\
            %s\n\
            \n\
            Employees : %s\n\
            Annual revenue : %s\n\
            Estimated annual revenue : %s\n\
            \n\
            Sector : \n\
            %s\n\
            \n\
            Tech : \n\
            %s\n\
            \n\
            Social networks :\n\
            www.facebook.com/%s\n\
            www.linkedin.com/%s\n\
            www.crunchbase.com/%s\n\
            www.twitter.com/%s\n\
            \n\
            Email addresses :\n\
            %s\n\
            \n\
            Phone numbers :\n\
            %s") % (company_data.get('description'),
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
            'vat': company_data.get('vat'),
            'logo': company_data.get('logo'),
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

    # @api.model
    # def read_by_vat(self, vat):
    #     vies_vat_data = False
    #
    #     try:
    #         url = 'http://odoo:8069/iap/partner_autocomplete/vat'
    #         params = {
    #             'vat': vat,
    #             'country_code': self.env.user.company_id.country_id.code,
    #         }
    #
    #         vies_vat_data = jsonrpc(url, params=params)
    #         vies_vat_data['_formatted'] = self._format_data_company(vies_vat_data)
    #     except (ConnectionError, HTTPError, exceptions.AccessError) as exception:
    #         _logger.error('Enrichment API error: %s' % str(exception))
    #         raise exceptions.UserError(_('Connection to Encrichment API failed.'))
    #
    #     return vies_vat_data

    @api.multi
    def write(self, values):
        res = super(ResPartner, self).write(values)

        vat = values.get('vat')
        if vat and self.company_data_id:
            vat_country_code = vat[:2]
            partner_country_code = self.country_id and self.country_id.code
            if self._is_company_in_europe(vat_country_code) and (partner_country_code == vat_country_code or not partner_country_code):
                try:
                    url = 'http://odoo:8069/iap/partner_autocomplete/update_vat'
                    params = {
                        'vat': values.get('vat'),
                        'company_data_id': self.company_data_id,
                    }
                    jsonrpc(url, params=params)
                except (ConnectionError, HTTPError, exceptions.AccessError) as exception:
                    _logger.error('Autocomplete API - VAT Update Error: %s' % str(exception))
        return res

    @api.model
    def _is_company_in_europe(self, country_code):
        country = self.env['res.country'].search([('code', '=', country_code)])
        if country:
            country_id = country.id
            europe = self.env.ref('base.europe')
            if not europe:
                europe = self.env["res.country.group"].search([('name', '=', 'Europe')], limit=1)
            if not europe or country_id not in europe.country_ids.ids:
                return False
        return True
