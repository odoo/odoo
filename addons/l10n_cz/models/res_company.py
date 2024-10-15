# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import account, base_vat


class ResCompany(account.ResCompany, base_vat.ResCompany):

    trade_registry = fields.Char()


class BaseDocumentLayout(account.BaseDocumentLayout):

    account_fiscal_country_id = fields.Many2one(related="company_id.account_fiscal_country_id")
    company_registry = fields.Char(related='company_id.company_registry')
