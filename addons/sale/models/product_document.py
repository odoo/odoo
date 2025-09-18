from odoo import fields, models


class ProductDocument(models.Model):
    _inherit = "product.document"

    attached_on_sale = fields.Selection(
        selection=[
            ("hidden", "Hidden"),
            ("quotation", "On quote"),
            ("sale_order", "On confirmed order"),
        ],
        string="Sale : Visible at",
        required=True,
        default="hidden",
        groups="sales_team.group_sale_salesman",
        help="Allows you to share the document with your customers within a sale.\n"
        "On quote: the document will be sent to and accessible by customers at any time.\n"
        "e.g. this option can be useful to share Product description files.\n"
        "On order confirmation: the document will be sent to and accessible by customers.\n"
        "e.g. this option can be useful to share User Manual or digital content bought"
        " on ecommerce. ",
    )
