from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    base_order_test_invoice_policy = fields.Selection(
        selection=[
            ("ordered", "Ordered quantities"),
            ("transferred", "Delivered quantities"),
        ],
        string="Base Order Test Invoicing Policy",
        default="ordered",
        help="`sale` and `purchase` each name their own policy field and this "
        "module depends on neither, so it declares the one its line model "
        "points `_invoice_policy_field` at.",
    )
