# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models

#in this file, we mostly add the tag translate=True on existing fields that we now want to be translated

class AccountAccountTag(models.Model):
    _inherit = 'account.account.tag'

    name = fields.Char(translate=True)

class AccountAccountTemplate(models.Model):
    _inherit = 'account.account.template'

    name = fields.Char(translate=True)


class AccountAccount(models.Model):
    _inherit = 'account.account'

    name = fields.Char(translate=True)

class AccountGroupTemplate(models.Model):
    _inherit = 'account.group.template'

    name = fields.Char(translate=True)

class AccountGroup(models.Model):
    _inherit = 'account.group'

    name = fields.Char(translate=True)

class AccountTax(models.Model):
    _inherit = 'account.tax'

    name = fields.Char(translate=True)
    description = fields.Char(translate=True)


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    name = fields.Char(translate=True)
    description = fields.Char(translate=True)


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'
    _order = 'name'

    name = fields.Char(translate=True)
    spoken_languages = fields.Char(string='Spoken Languages')
    # the languages for which the translations of templates could be loaded at
    # the time of installation of this localization module and copied in the
    # final object when generating them from templates. You must provide the
    # language codes separated by ';'


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    name = fields.Char(translate=True)
    note = fields.Html(translate=True)


class AccountFiscalPositionTemplate(models.Model):
    _inherit = 'account.fiscal.position.template'

    name = fields.Char(translate=True)
    note = fields.Text(translate=True)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    name = fields.Char(translate=True)


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    name = fields.Char(translate=True)


class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    name = fields.Char(translate=True)
