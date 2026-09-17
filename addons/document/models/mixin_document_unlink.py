from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MixinDocumentsUnlink(models.AbstractModel):
    _name = "mixin.documents.unlink"
    _description = "Documents unlink mixin"

    def unlink(self) -> bool:
        documents = (
            self.env["document.document"]
            .sudo()
            .with_context(active_test=False)
            .search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "in", self.ids),
                ]
            )
        )
        if documents:
            still_active = documents.filtered("active")
            _debug.lifecycle(
                "linked_documents_detached",
                model=self._name,
                records=self,
                documents=documents,
                trashed=len(documents) - len(still_active),
            )
            documents.write({"res_model": False, "res_id": False})
            still_active.action_archive()
        return super().unlink()
