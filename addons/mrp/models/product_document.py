
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductDocument(models.Model):
    _inherit = 'product.document'

    def _default_attached_on_mrp(self):
        return "bom" if self.env.context.get('attached_on_bom') else "hidden"

    attached_on_mrp = fields.Selection(
        selection=[
            ('hidden', "Hidden"),
            ('bom', "Bill of Materials")
        ],
        required=True,
        string="MRP : Visible at",
        help="Leave hidden if document only accessible on product form.\n"
            "Select Bill of Materials to visualise this document as a product attachment when this product is in a bill of material.",
        default=lambda self: self._default_attached_on_mrp(),
        groups='mrp.group_mrp_user',
    )
