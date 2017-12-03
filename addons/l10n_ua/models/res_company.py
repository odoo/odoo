# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CompanyUA(models.Model):
    _inherit = 'res.company'

    company_registry = fields.Char(related='partner_id.company_registry')
