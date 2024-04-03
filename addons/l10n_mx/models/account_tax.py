# coding: utf-8
from odoo import models, fields


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    l10n_mx_tax_type = fields.Selection(
        selection=[
            ('Tasa', "Tasa"),
            ('Cuota', "Cuota"),
            ('Exento', "Exento"),
        ],
        string="Factor Type",
        default='Tasa',
        help="The CFDI version 3.3 have the attribute 'TipoFactor' in the tax lines. In it is indicated the factor "
             "type that is applied to the base of the tax.")

    def _get_tax_vals(self, company, tax_template_to_tax):
        # OVERRIDE
        res = super()._get_tax_vals(company, tax_template_to_tax)
        res['l10n_mx_tax_type'] = self.l10n_mx_tax_type
        return res


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_mx_tax_type = fields.Selection(
        selection=[
            ('Tasa', "Tasa"),
            ('Cuota', "Cuota"),
            ('Exento', "Exento"),
        ],
        string="Factor Type",
        default='Tasa',
        help="The CFDI version 3.3 have the attribute 'TipoFactor' in the tax lines. In it is indicated the factor "
             "type that is applied to the base of the tax.")
