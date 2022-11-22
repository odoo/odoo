from odoo import fields, models


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    l10n_sa_edi_tax_category = fields.Selection([
        ('AE', 'Vat reverse charge'),
        ('E', 'Exempt from tax'),
        ('S', 'Standard rate'),
        ('Z', 'Zero rated goods'),
        ('G', 'Free export item, VAT not charged'),
        ('O', 'Services outside scope of tax'),
        ('K', 'VAT exempt for EEA intra-community supply of goods and services'),
        ('L', 'Canary Islands general indirect tax'),
        ('M', 'Tax for production, services and importation in Ceuta and Melilla'),
    ], string="Category", help="Tax category code, subset of UNCL5305", default="S", required=True)
