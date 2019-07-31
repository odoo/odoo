# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_tax_id = fields.Many2one('account.tax', string="Default Sale Tax", related='company_id.account_sale_tax_id', readonly=False)
    module_pos_mercury = fields.Boolean(string="Integrated Card Payments", help="The transactions are processed by Vantiv. Set your Vantiv credentials on the related payment journal.")
