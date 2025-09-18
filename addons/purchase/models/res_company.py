from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    order_lock_po = fields.Selection(
        selection=[
            ("edit", "Allow to edit purchase orders"),
            ("lock", "Confirmed purchase orders are not editable"),
        ],
        string="Purchase Order Modification",
        default="edit",
        help="Purchase Order Modification used when you want to purchase order editable after confirm",
    )
