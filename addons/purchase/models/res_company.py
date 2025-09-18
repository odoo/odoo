from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    po_quotation_validity_days = fields.Integer(
        string="Default RFQ Validity (Days)",
        default=0,
        help="Number of days for RFQ validity. Set to 0 for no default expiration.",
    )
    order_lock_po = fields.Selection(
        selection=[
            ("edit", "Allow to edit purchase orders"),
            ("lock", "Confirmed purchase orders are not editable"),
        ],
        string="Purchase Order Modification",
        default="edit",
        help="Purchase Order Modification used when you want to purchase order editable after confirm",
    )

    # ------------------------------------------------------------
    # CONSTRAINTS
    # ------------------------------------------------------------

    _check_po_quotation_validity_days = models.Constraint(
        "CHECK(po_quotation_validity_days >= 0)",
        "RFQ validity days must be a positive number.",
    )
