
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons.snailmail.country_utils import SNAILMAIL_COUNTRIES


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.multi
    def _get_country_name(self):
        # when sending a letter, thus rendering the report with the snailmail_layout,
        # we need to override the country name to its english version following the
        # dictionary imported in country_utils.py
        country_code = self.country_id.code
        if self.env.context.get('snailmail_layout') and country_code in SNAILMAIL_COUNTRIES:
            return SNAILMAIL_COUNTRIES.get(country_code)

        return super(ResPartner, self)._get_country_name()

    @api.model
    def _get_address_format(self):
        # When sending a letter, the fields 'street' and 'street2' should be on a single line to fit in the address area
        if self.env.context.get('snailmail_layout'):
            return "%(street)s, %(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s"

        return super(ResPartner, self)._get_address_format()