# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    l10n_il_income_tax_id_number = fields.Char(string='IncomeTax ID')
    l10n_il_registry_number = fields.Char(string='Registry Number')
    l10n_il_valid_until_date = fields.Date(string='Valid Until Date', readonly=False)
    l10n_il_withh_tax_reason = fields.Many2one('l10n.il.withh.tax.reason', string='Withh Tax Reason', help="This field contains the withholding tax reason that will be used for Annual Witholding Tax Report'")
    l10n_il_ita_branch = fields.Many2one('l10n.il.ita.branch', string='ITA Branch', help="This field contains the ITA branch that expended the withholding tax rate and that will be used for Annual Witholding Tax Report")
    l10n_il_tax_rate = fields.Many2one('account.tax', string='Tax Rate', help="Tax Rate")
