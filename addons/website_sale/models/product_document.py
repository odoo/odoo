# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductDocument(models.Model):
    _inherit = "product.document"

    attached_on_sale = fields.Selection(
        selection_add=[("shown_on_product_page", "On Product Page")],
        help="Allows you to share the document with your customers within a sale.\n"
        "From Quotation: the document will be sent to and accessible by customers at any time.\n"
        "e.g. this option can be useful to share Product description files.\n"
        "On Order Confirmation: the document will be sent to and accessible by customers.\n"
        "e.g. this option can be useful to share User Manual or digital content bought"
        " on ecommerce. \n"
        "On Product Page: the document will be accessible by customers on the product page.\n"
        "e.g. this option can be useful to share Product description files.",
        ondelete={"shown_on_product_page": "set default"},
    )
