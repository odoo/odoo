# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductDocument(models.Model):
    _inherit = "product.document"

    attached_on_sale = fields.Selection(
        selection=[
            ("hidden", "Never"),
            ("quotation", "From Quotation"),
            ("sale_order", "On Order Confirmation"),
        ],
        required=True,
        default="hidden",
        string="Accessible",
        help="Allows you to share the document with your customers within a sale.\n"
        "From Quotation: the document will be sent to and accessible by customers at any time.\n"
        "e.g. this option can be useful to share Product description files.\n"
        "On Order Confirmation: the document will be sent to and accessible by customers.\n"
        "e.g. this option can be useful to share User Manual or digital content bought"
        " on ecommerce. ",
        groups="sales_team.group_sale_salesman",
    )
