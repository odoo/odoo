# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_au_kp_payrun_identifier = fields.Integer('Employment Hero payrun id', help="Identifier of the Employment Hero payrun that created this move")


class AccountAccount(models.Model):
    _inherit = "account.account"

    l10n_au_kp_account_identifier = fields.Char('Matching Employment Hero Account', help="Identifier of the Employment Hero account that matches this account", size=64, index=True)
    l10n_au_kp_enable = fields.Boolean(related="company_id.l10n_au_kp_enable")


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_au_kp_tax_identifier = fields.Char('Matching Keypay Tax', help="Identifier of the keypay tax that matches this tax", size=64, index=True)
    l10n_au_kp_enable = fields.Boolean(related="company_id.l10n_au_kp_enable")
