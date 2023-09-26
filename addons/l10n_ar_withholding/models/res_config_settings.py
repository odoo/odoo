# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ar_tax_base_account_id = fields.Many2one(
        comodel_name='account.account',
        related='company_id.l10n_ar_tax_base_account_id',
        readonly=False,
        domain=[('deprecated', '=', False)],
        string="Tax Base Account",
        help="Account that will be set on lines created to represent the tax base amounts.")
