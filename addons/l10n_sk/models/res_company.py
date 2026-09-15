# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    trade_registry = fields.Char()
    income_tax_id = fields.Char(string="Income Tax ID", inverse='_inverse_income_tax_id')

    def _inverse_income_tax_id(self):
        for company in self:
            if company.partner_id._get_additional_identifier('SK_TIN') != (company.income_tax_id or None):
                company.partner_id._set_additional_identifier('SK_TIN', company.income_tax_id)


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    account_fiscal_country_id = fields.Many2one(related="company_id.account_fiscal_country_id")
    income_tax_id = fields.Char(related='company_id.income_tax_id')
