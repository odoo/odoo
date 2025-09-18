from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    days_to_purchase = fields.Float(
        string="Days to Purchase",
        help="Days needed to confirm a PO, define when a PO should be validated",
    )
