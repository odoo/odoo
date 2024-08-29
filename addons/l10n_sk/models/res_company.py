# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import web, base

from odoo import fields, models


class ResCompany(models.Model, base.ResCompany):

    trade_registry = fields.Char()
    income_tax_id = fields.Char(string="Income Tax ID")


class BaseDocumentLayout(models.TransientModel, web.BaseDocumentLayout):

    account_fiscal_country_id = fields.Many2one(related="company_id.account_fiscal_country_id")
    company_registry = fields.Char(related='company_id.company_registry')
    income_tax_id = fields.Char(related='company_id.income_tax_id')
