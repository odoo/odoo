from odoo import fields, models


class BarcodeRule(models.Model):
    _inherit = "barcode.rule"

    type = fields.Selection(
        selection_add=[("coupon", "Coupon")],
        ondelete={"coupon": "set default"},
    )
