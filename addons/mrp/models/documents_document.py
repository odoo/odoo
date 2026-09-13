from odoo import fields, models


class DocumentsDocument(models.Model):
    _inherit = "document.document"

    def _default_attached_on_mrp(self):
        return "bom" if self.env.context.get("attached_on_bom") else "hidden"

    attached_on_mrp = fields.Selection(
        selection=[("hidden", "Hidden"), ("bom", "Bill of Materials")],
        string="MRP : Visible at",
        default=lambda self: self._default_attached_on_mrp(),
        required=True,
        help="Leave hidden if document only accessible on product form.\n"
        "Select Bill of Materials to visualise this document as a product attachment when this product is in a bill of material.",
    )
