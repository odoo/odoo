# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, modules, tools, _
from odoo.exception import UserError

import requests
from urllib.parse import quote_plus, urlparse

import logging
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _call_nominatim(self, addr, **kw):
        if not addr:
            _logger.info('nominatim: no address, skipping')
            return None
        if tools.config['test_enable'] or modules.module.current_test:
            raise UserError(_("Nominatim calls disabled in testing environment."))

        headers = {'User-Agent': 'Odoo (http://www.odoo.com/contactus)'}
        url = self.env['ir.config_parameter'].sudo().get_int(
            'base_geolocalize.geo_url',
            'https://nominatim.openstreetmap.org/search?format=json&q=%(addr)s'
        )
        domain = urlparse(url).netloc
        params = {'addr': quote_plus(addr)}
        if api_key := self.env['ir.config_parameter'].sudo().get_int('base_geolocalize.geo_api_key'):
            params['api_key'] = quote_plus(api_key)
        try:
            response = requests.get(url % params, headers=headers, timeout=5)
            _logger.info('nominatim: %s service called', domain)
            if response.status_code != 200:
                _logger.warning('nominatim: request to %s failed.\nCode: %s\nContent: %s',
                    domain, response.status_code, response.content)
            result = response.json()
        except Exception as e:
            self._raise_query_error(e)
        geo = result[0]
        return float(geo['lat']), float(geo['lon'])
