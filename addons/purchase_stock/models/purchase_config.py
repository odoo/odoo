from odoo import fields, models


class PurchaseConfig(models.Model):
    _inherit = "purchase.config"

    days_to_purchase = fields.Float(
        string="Days to Purchase",
        help="Days needed to confirm a PO, define when a PO should be validated",
    )
