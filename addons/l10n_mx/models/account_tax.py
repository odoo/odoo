# coding: utf-8
from odoo import models, fields, api


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_mx_factor_type = fields.Selection(
        selection=[
            ('Tasa', "Tasa"),
            ('Cuota', "Cuota"),
            ('Exento', "Exento"),
        ],
        string="Factor Type",
        default='Tasa',
        help="Mexico: 'TipoFactor' is an attribute for CFDI 4.0. This indicates the factor type that is applied to the base of the tax.",
    )
    l10n_mx_tax_type = fields.Selection(
        selection=[
            ('isr', "ISR"),
            ('iva', "IVA"),
            ('ieps', "IEPS"),
            ('local', "Local"),
        ],
        string="SAT Tax Type",
        compute="_compute_l10n_mx_tax_type",
        store=True,
        readonly=False,
    )

    @api.depends("country_id")
    def _compute_l10n_mx_tax_type(self):
        for tax in self:
            tax.l10n_mx_tax_type = 'iva' if tax.country_id.code == 'MX' else False

    @api.model
    def _round_tax_details_tax_amounts(self, base_lines, company, mode='mixed'):
        # EXTENDS 'account'
        country_code = company.account_fiscal_country_id.code
        if country_code == 'MX':
            mode = 'excluded'
        super()._round_tax_details_tax_amounts(base_lines, company, mode=mode)

    @api.model
    def _round_tax_details_base_lines(self, base_lines, company, mode='mixed'):
        # EXTENDS 'account'
        country_code = company.account_fiscal_country_id.code
        if country_code == 'MX':
            mode = 'excluded'
        super()._round_tax_details_base_lines(base_lines, company, mode=mode)
