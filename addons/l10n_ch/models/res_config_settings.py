# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ch_isr_preprinted_account = fields.Boolean(string='Preprinted account',
        related="company_id.l10n_ch_isr_preprinted_account")
    l10n_ch_isr_preprinted_bank = fields.Boolean(string='Preprinted bank',
        related="company_id.l10n_ch_isr_preprinted_bank")
    l10n_ch_isr_print_bank_location = fields.Boolean(string="Print bank on ISR",
        related="company_id.l10n_ch_isr_print_bank_location",
        required=True)
    l10n_ch_isr_scan_line_left = fields.Float(string='Horizontal offset',
        related="company_id.l10n_ch_isr_scan_line_left")
    l10n_ch_isr_scan_line_top = fields.Float(string='Vertical offset',
        related="company_id.l10n_ch_isr_scan_line_top")
