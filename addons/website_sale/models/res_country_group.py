# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCountryGroup(models.Model):
    _inherit = 'res.country.group'

    website_pricelist_ids = fields.Many2many('website_pricelist', 'res_country_group_website_pricelist_rel',
                                             'res_country_group_id', 'website_pricelist_id', string='Website Price Lists')
