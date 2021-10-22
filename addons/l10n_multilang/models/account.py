# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models

#in this file, we mostly add the tag translate=True on existing fields that we now want to be translated

class AccountAccountTag(models.Model):
    _inherit = 'account.account.tag'

    name = fields.Char(translate=True)


class AccountAccount(models.Model):
    _inherit = 'account.account'

    name = fields.Char(translate=True)

class AccountGroup(models.Model):
    _inherit = 'account.group'

    name = fields.Char(translate=True)

class AccountTax(models.Model):
    _inherit = 'account.tax'

    name = fields.Char(translate=True)
    description = fields.Char(translate=True)


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    name = fields.Char(translate=True)
    note = fields.Html(translate=True)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    name = fields.Char(translate=True)


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    name = fields.Char(translate=True)


class AccountTaxReport(models.Model):
    _inherit = 'account.tax.report'

    name = fields.Char(translate=True)


class AccountTaxReportLine(models.Model):
    _inherit = 'account.tax.report.line'

    name = fields.Char(translate=True)
    tag_name = fields.Char(translate=True)


class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    name = fields.Char(translate=True)
