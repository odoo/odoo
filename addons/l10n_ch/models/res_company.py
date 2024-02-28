# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class Company(models.Model):
    _inherit = "res.company"

    l10n_ch_isr_preprinted_account = fields.Boolean(string='Preprinted account', compute='_compute_l10n_ch_isr', inverse='_set_l10n_ch_isr')
    l10n_ch_isr_preprinted_bank = fields.Boolean(string='Preprinted bank', compute='_compute_l10n_ch_isr', inverse='_set_l10n_ch_isr')
    l10n_ch_isr_print_bank_location = fields.Boolean(string='Print bank location', default=False, help='Boolean option field indicating whether or not the alternate layout (the one printing bank name and address) must be used when generating an ISR.')
    l10n_ch_isr_scan_line_left = fields.Float(string='Scan line horizontal offset (mm)', compute='_compute_l10n_ch_isr', inverse='_set_l10n_ch_isr')
    l10n_ch_isr_scan_line_top = fields.Float(string='Scan line vertical offset (mm)', compute='_compute_l10n_ch_isr', inverse='_set_l10n_ch_isr')

    def _compute_l10n_ch_isr(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        for company in self:
            company.l10n_ch_isr_preprinted_account = bool(get_param('l10n_ch.isr_preprinted_account', default=False))
            company.l10n_ch_isr_preprinted_bank = bool(get_param('l10n_ch.isr_preprinted_bank', default=False))
            company.l10n_ch_isr_scan_line_top = float(get_param('l10n_ch.isr_scan_line_top', default=0))
            company.l10n_ch_isr_scan_line_left = float(get_param('l10n_ch.isr_scan_line_left', default=0))

    def _set_l10n_ch_isr(self):
        set_param = self.env['ir.config_parameter'].sudo().set_param
        for company in self:
            set_param("l10n_ch.isr_preprinted_account", company.l10n_ch_isr_preprinted_account)
            set_param("l10n_ch.isr_preprinted_bank", company.l10n_ch_isr_preprinted_bank)
            set_param("l10n_ch.isr_scan_line_top", company.l10n_ch_isr_scan_line_top)
            set_param("l10n_ch.isr_scan_line_left", company.l10n_ch_isr_scan_line_left)
