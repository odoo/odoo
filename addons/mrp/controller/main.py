from odoo.addons.document_product.controllers.document_document import (
    ProductDocumentsController,
)


class MRPProductDocumentController(ProductDocumentsController):
    def _prepare_additional_document_vals(self, **kwargs):
        super_values = super()._prepare_additional_document_vals(**kwargs)
        if kwargs.get("attached_on_bom"):
            return super_values | {"attached_on_mrp": "bom"}
        return super_values
