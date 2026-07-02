# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Command


class ProductDocument(models.Model):
    _inherit = "product.document"

    form_field_ids = fields.Many2many(
        string="Fields",
        comodel_name="sale.pdf.form.field",
        domain=[("document_type", "=", "product_document")],
        compute="_compute_form_field_ids",
        store=True,
    )

    # === COMPUTE METHODS === #

    @api.depends("raw", "attached_on_sale")
    def _compute_form_field_ids(self):
        # Empty the linked form fields as we want all and only those from the current raw data
        self.form_field_ids = [Command.clear()]
        document_to_parse = self.filtered(
            lambda doc: doc.raw and doc.mimetype and doc.mimetype.endswith("pdf")
        )
        if document_to_parse:
            doc_type = "product_document"
            self.env["sale.pdf.form.field"]._create_or_update_form_fields_on_pdf_records(
                document_to_parse, doc_type
            )

    # === ACTION METHODS ===#

    def action_open_pdf_form_fields(self):
        self.ensure_one()
        return {
            "name": self.env._("Form Fields"),
            "type": "ir.actions.act_window",
            "res_model": "sale.pdf.form.field",
            "view_mode": "list",
            "context": {
                "default_document_type": "product_document",
                "default_product_document_ids": self.id,
                "default_quotation_document_ids": False,
                "search_default_context_document": True,
            },
            "target": "current",
        }
