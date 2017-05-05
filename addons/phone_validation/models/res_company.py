# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    phone_international_format = fields.Boolean(
        string="Enforce International Format", default=False,
        help="Always encore phone numbers using international format. Otherwise"
             "numbers coming from the company's country are nationaly formatted."
             "International numbers are always using international format."
    )
