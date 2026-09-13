from odoo import api, fields, models
from odoo.fields import Domain


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_product_settings = fields.Boolean()
    product_folder_id = fields.Many2one(
        comodel_name="document.document",
        compute="_compute_product_folder_id",
        store=True,
        readonly=False,
        domain=[("type", "=", "folder"), ("shortcut_document_id", "=", False)],
        check_company=True,
    )
    product_tag_ids = fields.Many2many(
        comodel_name="document.tag",
        relation="product_tags_table",
    )

    @api.depends("documents_product_settings")
    def _compute_product_folder_id(self):
        folder_id = self.env.ref(
            "document_product.document_product_folder", raise_if_not_found=False
        )
        self._reset_default_documents_folder_id(
            "documents_product_settings", "product_folder_id", folder_id
        )

    def _get_domain_used_folder_ids(self, folder_ids):
        return super()._get_domain_used_folder_ids(folder_ids) | (
            Domain("product_folder_id", "in", folder_ids)
            & Domain("documents_product_settings", "=", True)
        )
