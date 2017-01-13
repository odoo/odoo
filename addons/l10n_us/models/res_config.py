# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    module_account_taxcloud = fields.Boolean("Compute sales tax automatically in the United States using TaxCloud.",
        help='TaxCloud is an online provider that is committed to making it easy for retailers to collect sales tax online'
             'in the United States.')
