# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    l10n_ch_isr_print_bank_location = fields.Boolean(string="Print bank on ISR",
        related="company_id.l10n_ch_isr_print_bank_location",
        required=True)
