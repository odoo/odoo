from odoo import api, fields, models
from odoo.libs.documents import Document

from ..tools.schema import known_schemas
from ..tools.source import document_of


class IrAttachment(models.Model):
    _name = "ir.attachment"
    _inherit = ["ir.attachment", "mixin.extract"]

    extract_document_type = fields.Selection(
        selection="_selection_extract_document_type",
        copy=False,
        help="Which kind of document this is. Determines the fields an "
        "extraction is expected to produce.",
    )

    @api.model
    def _selection_extract_document_type(self) -> list[tuple[str, str]]:
        return [(name, name.replace("_", " ").title()) for name in known_schemas()]

    def _get_extract_document_type(self) -> str:
        return self.extract_document_type or ""

    def _get_extract_source(self) -> Document | None:
        self.check_singleton()
        if not self.raw:
            return None
        return document_of(self)
