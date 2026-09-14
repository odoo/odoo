from odoo import _, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class DocumentDocument(models.Model):
    _inherit = "document.document"

    def action_link_to_record(self, model: str | bool = False) -> dict:
        """Open the `link_to_record_wizard` to choose a record to link to the current documents.

        This method can be used inside server actions.
        """
        context = {
            "default_document_ids": self.ids,
            "default_resource_ref": False,
            "default_is_readonly_model": False,
            "default_model_ref": False,
        }

        if documents_link_record := self.filtered("res_model"):
            _debug.logic(
                "link_refused", reason="already_linked", documents=documents_link_record
            )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "warning",
                    "message": _(
                        "Already linked Documents: %s",
                        ", ".join(documents_link_record.mapped("name")),
                    ),
                },
            }

        if model:
            self.env[model].check_access("write")
            context["default_is_readonly_model"] = True
            context["default_model_id"] = self.env["ir.model"]._get_id(model)
            first_valid_id = self.env[model].search([], limit=1).id
            if not first_valid_id:
                _debug.logic("link_refused", reason="no_target_record", model=model)
                raise UserError(
                    _("There are no records to link this document. Create one first.")
                )
            context["default_resource_ref"] = f"{model},{first_valid_id}"

        return {
            "name": _("Choose a record to link"),
            "type": "ir.actions.act_window",
            "res_model": "document.link_to_record_wizard",
            "view_mode": "form",
            "target": "new",
            "views": [(False, "form")],
            "context": context,
        }
