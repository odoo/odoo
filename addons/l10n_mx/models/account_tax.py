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
        help="The CFDI version 3.3 have the attribute 'TipoFactor' in the tax lines. In it is indicated the factor "
             "type that is applied to the base of the tax.")
    l10n_mx_tax_type = fields.Selection(
        selection=[
            ('isr', "ISR"),
            ('iva', "IVA"),
            ('ieps', "IEPS"),
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
