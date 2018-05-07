# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import api, models

_logger = logging.getLogger(__name__)

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
    def _parse_partner_vals(self, vies_result):
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

        if not vies_result:
            return False, {}
        partner_name = False
        partner_address = {}
        if vies_result['name'] != '---':
            partner_name = vies_result['name']

        #parse the address from VIES and fill the partner's data
        if vies_result['address'] == '---': return partner_name, {}

        lines = [x for x in vies_result['address'].split("\n") if x]
        if len(lines) == 1:
            lines = [x.strip() for x in lines[0].split(',') if x]
        if len(lines) == 1:
            lines = [x.strip() for x in lines[0].split('   ') if x]

        partner_address['street'] = lines.pop(0)
        #_set_address_field(partner, 'street', lines.pop(0))

        if len(lines) > 0:
            res = _check_city(lines, vies_result['countryCode'])
            if res:
                partner_address['zip'] = res[0]
                partner_address['city'] = res[1]
                #_set_address_field(partner, 'zip', res[0])
                #_set_address_field(partner, 'city', res[1])
        if len(lines) > 0:
            partner_address['street2'] = lines.pop(0)
            #_set_address_field(partner, 'street2', lines.pop(0))

        country = self.env['res.country'].search([('code', '=', vies_result['countryCode'])], limit=1)

        #_set_address_field(partner, 'country_id', country and country.id or False)
        partner_address['country_id'] = country and country.id or False
        return partner_name, partner_address

    def _check_vat(self, check_func):
        res = super(ResPartner, self)._check_vat(check_func)
        company = self.env.context.get('company_id', self.env.user.company_id)
        if res and company.vat_check_vies:
            # If a field is not set in the response, wipe it anyway
            non_set_address_fields = set(['street', 'street2', 'city', 'zip', 'state_id', 'country_id'])
            partner_name, partner_address = self._parse_partner_vals(res)
            if not self.name and partner_name:
                self.name = partner_name

            if partner_address:
                #set the address fields
                for field, value in partner_address.items():
                    self[field] = value
                    non_set_address_fields.remove(field)
                for field in non_set_address_fields:
                    if self[field]:
                        self[field] = False
        return res


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.onchange('vat')
    def vies_vat_change(self):
        self.ensure_one()
        company_address_fields = set(['street', 'street2', 'city', 'zip', 'state_id', 'country_id'])
        company_name, company_address = self.env['res.partner']._get_partner_vals(self.vat)
        if not self.name and company_name:
            self.name = company_name
        #set the address fields
        for field, value in company_address.items():
            self[field] = value
            company_address_fields.remove(field)
        for field in company_address_fields:
            if self[field]:
                self[field] = False
