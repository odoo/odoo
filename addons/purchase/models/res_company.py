from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    po_quotation_validity_days = fields.Integer(
        string="Default RFQ Validity (Days)",
        help="Number of days for RFQ validity. Set to 0 for no default expiration.",
        default=0,
    )
    order_lock_po = fields.Selection(
        selection=[
            ("edit", "Allow to edit purchase orders"),
            ("lock", "Confirmed purchase orders are not editable"),
        ],
        string="Purchase Order Modification",
        help="Purchase Order Modification used when you want to purchase order editable after confirm",
        default="edit",
    )

    _check_po_quotation_validity_days = models.Constraint(
        "CHECK(po_quotation_validity_days >= 0)",
        "RFQ validity days must be zero or greater (0 means no default expiration).",
    )
