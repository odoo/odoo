from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MixinDocumentsProduct(models.AbstractModel):
    _name = "mixin.documents.product"
    _inherit = "mixin.documents"
    _description = "Product documents creation mixin"

    # The domain resolves per concrete model, so one declaration serves both
    # product.template and product.product.
    product_document_ids = fields.One2many(
        comodel_name="document.document",
        inverse_name="res_id",
        string="Documents",
        domain=lambda self: [("res_model", "=", self._name)],
    )
    product_document_count = fields.Integer(
        string="Documents Count",
        compute="_compute_product_document_count",
    )

    def _compute_product_document_count(self):
        raise NotImplementedError

    def _get_document_vals_access_rights(self):
        return {
            "access_internal": "view",
            "access_via_link": "view",
        }

    def _get_document_owner(self):
        return self.env.user

    def _get_document_tags(self):
        company = self.company_id or self.env.company
        return company.product_tag_ids

    def _get_document_folder(self):
        # `documents_product_settings` chooses a dedicated folder; it does not
        # decide whether the document exists. A company that never enabled it
        # files product documents in the seeded folder instead, so turning the
        # setting off cannot make product documents stop being created.
        company = self.company_id or self.env.company
        if _debug.logic.enabled:
            _debug.logic(
                "product_folder",
                by="company" if company.product_folder_id else "seeded",
                company=company,
            )
        return (
            company.product_folder_id
            or self.env.ref(
                "document_product.document_product_folder",
                raise_if_not_found=False,
            )
            or self.env["document.document"]
        )
