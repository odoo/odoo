# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_rs_company_registry = fields.Char(string='Company ID', help='The registry number of the company.')

    _sql_constraints = [
        (
            'company_registry_country_uniq',
            'unique (l10n_rs_company_registry, country_id)',
            'The company registry of the partner must be unique across all partners of a same country !'
         )
    ]
