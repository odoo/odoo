# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2018 Linserv Aktiebolag, Sweden (https://www.linserv.se/).

from odoo import models, api


class ResCountryGroup(models.Model):
    _inherit = "res.country.group"

    @api.model
    def _load_non_europe(self):
        """
        Auto set countries that is not part of EU when Installing/Upgrade
        """
        country_group_eu = self.env.ref('base.europe') or False
        country_group_non_eu = self.env.ref('l10n_se.non_europe')

        eu_countries = country_group_eu and country_group_eu.country_ids and country_group_eu.country_ids.ids or []
        non_eu_countries = self.env['res.country'].search([('id', 'not in', eu_countries)])

        country_group_non_eu.write({'country_ids': [[6, 0, non_eu_countries and non_eu_countries.ids or []]]})
