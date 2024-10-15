# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import account, base_vat


class ResCompany(base_vat.ResCompany, account.ResCompany):

    trade_registry = fields.Char()
    income_tax_id = fields.Char(string="Income Tax ID")


class BaseDocumentLayout(account.BaseDocumentLayout):

    account_fiscal_country_id = fields.Many2one(related="company_id.account_fiscal_country_id")
    company_registry = fields.Char(related='company_id.company_registry')
    income_tax_id = fields.Char(related='company_id.income_tax_id')
