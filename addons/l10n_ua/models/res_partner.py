# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PartnerUA(models.Model):
    _inherit = "res.partner"

    company_registry = fields.Char(
        'Company Registry',
        help='Registry Number')
