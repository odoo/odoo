from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class DocumentsDocument(models.Model):
    _inherit = "document.document"

    is_gelato = fields.Boolean(readonly=True)

    def _gelato_prepare_file_payload(self):
        if not self.datas:
            _debug.logic("gelato_file_payload_refused", document=self)
            raise UserError(
                _("Print images must be set on products before they can be ordered.")
            )

        query_string = f"access_token={self.attachment_id.generate_access_token()[0]}"
        url = f"{self.get_base_url()}{self.attachment_id.image_src}?{query_string}"
        return {
            "type": self.name.lower(),
            "url": url,
        }
