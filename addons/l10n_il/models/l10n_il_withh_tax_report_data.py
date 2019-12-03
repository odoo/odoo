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
