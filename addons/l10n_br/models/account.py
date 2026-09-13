from odoo import fields, models


class AccountTax(models.Model):
    """Add fields used to define some brazilian taxes"""

    _inherit = "account.tax"

    tax_discount = fields.Boolean(
        string="Discount this Tax in Price",
        help="Mark it for (ICMS, PIS e etc.).",
    )
    base_reduction = fields.Float(
        string="Redution",
        help="Um percentual decimal em % entre 0-1.",
        digits=0,
        default=0,
        required=True,
    )
    amount_mva = fields.Float(
        string="MVA Percent",
        help="Um percentual decimal em % entre 0-1.",
        digits=0,
        default=0,
        required=True,
    )
