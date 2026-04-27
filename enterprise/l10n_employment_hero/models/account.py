# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    employment_hero_payrun_identifier = fields.Integer('Employment Hero payrun id', help="Identifier of the Employment Hero payrun that created this move")


class AccountAccount(models.Model):
    _inherit = "account.account"

    employment_hero_account_identifier = fields.Char('Matching Employment Hero Account', help="Identifier of the Employment Hero account that matches this account", size=64, index=True)
    employment_hero_enable = fields.Boolean(compute='_compute_employment_hero_enable')

    def _compute_employment_hero_enable(self):
        for record in self:
            record.employment_hero_enable = any(record.company_ids.mapped('employment_hero_enable'))


class AccountTax(models.Model):
    _inherit = "account.tax"

    employment_hero_tax_identifier = fields.Char('Matching Employment Hero Tax', help="Identifier of the Employment Hero tax that matches this tax", size=64, index=True)
    employment_hero_enable = fields.Boolean(related="company_id.employment_hero_enable")
