# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models

#in this file, we mostly add the tag translate=True on existing fields that we now want to be translated


class AccountAccountTemplate(models.Model):
    _inherit = 'account.account.template'

    name = fields.Char(required=True, index=True, translate=True)


class AccountAccount(models.Model):
    _inherit = 'account.account'

    name = fields.Char(required=True, index=True, translate=True)


class AccountTax(models.Model):
    _inherit = 'account.tax'

    name = fields.Char(string='Tax Name', required=True, index=True, translate=True)


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    name = fields.Char(string='Tax Name', required=True, index=True, translate=True)


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    spoken_languages = fields.Char(string='Spoken Languages', help="State here the languages for which the translations of templates could be loaded at the time of installation of this localization module and copied in the final object when generating them from templates. You must provide the language codes separated by ';'")


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    name = fields.Char(string='Fiscal Position', required=True, translate=True)
    note = fields.Text(string='Notes', translate=True)


class AccountFiscalPositionTemplate(models.Model):
    _inherit = 'account.fiscal.position.template'

    name = fields.Char(string='Fiscal Position Template', required=True, translate=True)
    note = fields.Text(string='Notes', translate=True)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    name = fields.Char(string='Journal Name', required=True, translate=True)


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    name = fields.Char(string='Account Name', required=True, translate=True)
