from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_mg_tax_regime = fields.Selection(
        selection=[
            ("ir", "Impôt sur les Revenus (IR) & TVA"),
            ("is", "Impôt Synthétique (IS)"),
        ],
        string="Tax Regime",
        default="ir",
        help="Malagasy tax regime, which determines the returns to file. The Impôt Synthétique replaces the "
        "income tax and the VAT for annual turnovers below Ar 400 000 000 (CDI art. 01.02.02).",
    )
