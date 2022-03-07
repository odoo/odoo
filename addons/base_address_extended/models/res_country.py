# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Country(models.Model):
    _inherit = 'res.country'

    extended_address = fields.Boolean(
        string='Use Extended Address Format',
        help="Check this box to format address with street name, street number and door number")
