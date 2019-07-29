# -*- coding: utf-8 -*-

from odoo import fields, models


class WithhReason(models.Model):
    _name = 'l10n.il.withh.tax.reason'

    name = fields.Char(string='Withh Tax Reason')
    code = fields.Char(string='Code for Withh Tax Reason')

    _sql_constraints = [('code_name_uniq', 'unique (code,name)', 'The code of the Withholding Tax Reason must be unique!')]


class ITABranch(models.Model):
    _name = 'l10n.il.ita.branch'

    name = fields.Char(string='ITA Branch')
    code = fields.Char(string='ITA Branch Code')

    _sql_constraints = [('code_name_uniq', 'unique (code,name)', 'The code of the ITA Branch must be unique!')]


class WithhTaxReportData(models.Model):
    _inherit = 'account.tax'

    l10n_il_valid_until_date = fields.Date(string='Valid Until Date', readonly=False)
    l10n_il_withh_tax_reason = fields.Many2one('l10n.il.withh.tax.reason', string='Withh Tax Reason', help="This field contains the withholding tax reason that will be used for Annual Witholding Tax Report'")
    l10n_il_ita_branch = fields.Many2one('l10n.il.ita.branch', string='ITA Branch', help="This field contains the ITA branch that expended the withholding tax rate and that will be used for Annual Witholding Tax Report")
