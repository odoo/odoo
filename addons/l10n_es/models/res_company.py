from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_es_simplified_invoice_limit = fields.Float(
        string="Simplified Invoice limit amount",
        default=400,
        help="Over this amount is not legally possible to create a simplified invoice",
    )
