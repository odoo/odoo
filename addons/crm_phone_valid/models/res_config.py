# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"
    crm_phone_valid_method = fields.Selection([
        ('national', 'National'),
        ('international', 'International'),
    ], string="National Phone Format", default="national", help="Format of phone numbers of your country. (all others are international)", required=True)


class CRMSettings(models.TransientModel):
    _inherit = 'sale.config.settings'
    crm_phone_valid_method = fields.Selection(related="company_id.crm_phone_valid_method", required=True)
