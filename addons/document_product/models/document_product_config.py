from odoo import api, fields, models


class DocumentProductConfig(models.Model):
    _name = "document_product.config"
    _description = "A company's document product configuration"
    _inherit = ["mixin.company.config", "mixin.document.default.folder"]

    documents_product_settings = fields.Boolean()
    product_folder_id = fields.Many2one(
        comodel_name="document.document",
        compute="_compute_product_folder_id",
        store=True,
        readonly=False,
        domain=[("type", "=", "folder"), ("shortcut_document_id", "=", False)],
        check_company=True,
    )
    product_tag_ids = fields.Many2many(comodel_name="document.tag")

    @api.depends("documents_product_settings")
    def _compute_product_folder_id(self):
        folder_id = self.env.ref(
            "document_product.document_product_folder", raise_if_not_found=False
        )
        self._reset_default_documents_folder_id(
            "documents_product_settings", "product_folder_id", folder_id
        )
