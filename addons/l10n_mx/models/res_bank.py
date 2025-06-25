# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Bank(models.Model):
    _inherit = "res.bank"

    def _get_fiscal_country_codes(self):
        return ','.join(self.env.companies.mapped('account_fiscal_country_id.code'))

    l10n_mx_edi_code = fields.Char(
        "ABM Code",
        help="Three-digit number assigned by the ABM to identify banking "
        "institutions (ABM is an acronym for Asociación de Bancos de México)")
    fiscal_country_codes = fields.Char(store=False, default=_get_fiscal_country_codes)


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    def _get_fiscal_country_codes(self):
        return ','.join(self.env.companies.mapped('account_fiscal_country_id.code'))

    l10n_mx_edi_clabe = fields.Char(
        "CLABE", help="Standardized banking cipher for Mexico. More info "
        "wikipedia.org/wiki/CLABE")
    fiscal_country_codes = fields.Char(store=False, default=_get_fiscal_country_codes)
