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
                'vat': vat,
                'country_code': self.env.user.company_id.country_id.code,
            }

            vies_vat_data = jsonrpc(url, params=params)

        except (ConnectionError, HTTPError, exceptions.AccessError) as exception:
            _logger.error('Enrichment API error: %s' % str(exception))
            raise exceptions.UserError(_('Connection to Encrichment API failed.'))

        return vies_vat_data

# FOR TESTING PURPOSE ========================================================

import re
from odoo import api, models
from suds.client import Client

try:
    import stdnum.eu.vat as stdnum_vat
    if not hasattr(stdnum_vat, "country_codes"):
        # stdnum version >= 1.9
        stdnum_vat.country_codes = stdnum_vat._country_codes
except ImportError:
    _logger.warning('Python `stdnum` library not found, unable to call VIES service to detect address based on VAT number.')
    stdnum_vat = None

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def vies_vat_search(self, vat):
        def _check_city(lines, country='BE'):
            if country == 'GB':
                ukzip = '[A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][A-Z]{2}'
                if re.match(ukzip, lines[-1]):
                    cp = lines.pop()
                    city = lines.pop()
                    return (cp, city)
            elif country == 'SE':
                result = re.match('([0-9]{3}\s?[0-9]{2})\s?([A-Z]+)', lines[-1])
                if result:
                    lines.pop()
                    return (result.group(1), result.group(2))
            else:
                result = re.match('((?:L-|AT-)?[0-9\-]+[A-Z]{,2}) (.+)', lines[-1])
                if result:
                    lines.pop()
                    return (result.group(1), result.group(2))
            return False

        # Equivalent to stdnum_vat.check_vies(partner.vat).
        # However, we want to add a custom timeout to the suds.client
        # because by default, it's 120 seconds and this is to long.
        try:
            client = Client(stdnum_vat.vies_wsdl, timeout=5)
            partner_vat = stdnum_vat.compact(vat)
            result = client.service.checkVat(partner_vat[:2], partner_vat[2:])
        except:
            # Avoid blocking the client when the service is unreachable/unavailable
            return False

        if not result['valid']:
            return False

        if result['name'] != '---':
            partner = {}

            # TODO: PUT THIS IN IAPS !!!!
            # Put the legal form in the company name at the end
            split_name = result['name'].split(' ')
            legal_form = split_name.pop(0)
            partner['short_name'] = ' '.join(split_name)

            split_name.append(legal_form)
            partner['name'] = ' '.join(split_name)
            partner['vat'] = result['countryCode'] + result['vatNumber']

            lines = [x for x in result['address'].split("\n") if x]
            if len(lines) == 1:
                lines = [x.strip() for x in lines[0].split(',') if x]
            if len(lines) == 1:
                lines = [x.strip() for x in lines[0].split('   ') if x]

            vals = self._split_street_with_params(', '.join(lines.pop(0).rsplit(' ', 1)), '%(street_name)s, %(street_number)s/%(street_number2)s')
            partner.update(vals)

            if len(lines) > 0:
                res = _check_city(lines, result['countryCode'])
                if res:
                    partner['zip'] = res[0]
                    partner['city'] = res[1].title()
            if len(lines) > 0:
                partner['street2'] = lines.pop(0).title()

            country = self.env['res.country'].search([('code', '=', result['countryCode'])], limit=1)
            partner['country_id'] = country and country.id or False

            return partner

        return False