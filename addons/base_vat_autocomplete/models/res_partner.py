# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging
import string
import re

from odoo import api, models, _
from odoo.tools.misc import ustr
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _check_city(self, lines, country='BE'):
        if country=='GB':
            ukzip = '[A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][A-Z]{2}'
            if re.match(ukzip, lines[-1]):
                cp = lines.pop()
                city = lines.pop()
                return (cp, city)
        else:
            result = re.match('((?:L-|AT-)?[0-9\-]+) (.+)', lines[-1])
            if result:
                lines.pop()
                return (result.group(1), result.group(2))
        return False

    @api.onchange('vat')
    def vies_vat_change(self):
        if len(self.vat or '')>5:
            try:
                import stdnum.eu.vat
                result = stdnum.eu.vat.check_vies(self.vat)
            except ImportError:
                _logger.warning('Python stdnum library not found, unable to call VIES service to detect address based on VAT number.')
            except:
                return {}
            if not result['valid']:
                return {'warning': {
                    'title': _('Invalid VAT number!'),
                    'message': _('The VAT number has been tested invalid by the European Commission VIES service: http://ec.europa.eu/taxation_customs/vies/')
                }}

            if (not self.name) and (result['name'] != '---'):
                self.name = result['name']
            if result['address'] == '---': return {}

            lines = [x for x in result['address'].split("\n") if x]
            if len(lines)==1:
                lines = [x.strip() for x in lines[0].split(',') if x]
            if len(lines)==1:
                lines = [x.strip() for x in lines[0].split('   ') if x]
            self.street = lines.pop(0)
            if len(lines)>0:
                res = self._check_city(lines, result['countryCode'])
                if res:
                    self.zip = res[0]
                    self.city = res[1]
            if len(lines)>0:
                self.street2 = lines.pop(0)

            country = self.env['res.country'].search([('code','=',result['countryCode'])], limit=1)
            self.country_id = country and country.id or False
        return {}
