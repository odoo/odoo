# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class ProductDocument(models.Model):
    _inherit = 'product.document'

    attached_on = fields.Selection(
        selection_add=[('inside', "Inside quote")],
        help="Allows you to share the document with your customers within a sale.\n"
             "Leave it empty if you don't want to share this document with sales customer.\n"
             "Quotation: the document will be sent to and accessible by customers at any time.\n"
             "e.g. this option can be useful to share Product description files.\n"
             "Confirmed order: the document will be sent to and accessible by customers.\n"
             "e.g. this option can be useful to share User Manual or digital content bought"
             " on ecommerce. \n"
             "Inside quote: The document will be included in the pdf of the quotation between the "
             "header pages and the quote table. ",
    )

    def write(self, vals):
        res = super().write(vals)
        if vals.keys() & {'attached_on', 'mimetype'}:
            if any(
                doc.attached_on == 'inside' and not doc.mimetype.endswith('pdf') for doc in self
            ):
                raise ValidationError(_("Only PDF documents can be attached inside a quote."))
        return res
