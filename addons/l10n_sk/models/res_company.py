# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    trade_registry = fields.Char()
    income_tax_id = fields.Char(string="Income Tax ID")
    l10n_sk_nace_code = fields.Char(string="SK NACE Code")

    @api.constrains('l10n_sk_nace_code')
    def _check_l10n_sk_nace_code(self):
        for company in self:
            if company.l10n_sk_nace_code and len(company.l10n_sk_nace_code) != 5:
                raise UserError(_("Please make sure that the copmany's SK NACE Code has 5 digits."))


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    account_fiscal_country_id = fields.Many2one(related="company_id.account_fiscal_country_id")
    company_registry = fields.Char(related='company_id.company_registry')
    income_tax_id = fields.Char(related='company_id.income_tax_id')
