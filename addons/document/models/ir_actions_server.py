from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    usage = fields.Selection(
        selection_add=[("documents_embedded", "Documents")],
        ondelete={"documents_embedded": "set ir_actions_server"},
    )

    def action_view_documents_server_action_view(self) -> dict:
        self.check_access("read")
        form_view = self.env.ref(
            "document.ir_actions_server_view_form_documents", raise_if_not_found=False
        )
        search_view = self.env.ref(
            "document.ir_actions_server_action_search_documents",
            raise_if_not_found=False,
        )
        return {
            "context": {
                "default_model_id": self.env["ir.model"]._get_id("document.document"),
                "default_update_path": "tag_ids",
                "default_usage": "documents_embedded",
            },
            "display_name": _("Server Actions"),
            "domain": [
                ("model_name", "=", "document.document"),
                ("parent_id", "=", False),
            ],
            "help": """
                <div style="width:650px;">
                    <p class="d-none">%s</p>
                    <img class="w-100 w-md-75" src="/document/static/img/document_server_action.svg"/>
                </div>
            """
            % _("No server actions found for Documents!"),
            "res_model": "ir.actions.server",
            "target": "current",
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "views": [(False, "list"), (form_view.id if form_view else False, "form")],
            "search_view_id": [search_view.id if search_view else False, "search"],
        }

    def _run(self, records: models.Model, eval_context: dict) -> dict | bool:
        # A pinned action is the folder editor's delegation: the caller has been
        # checked for the pin and for write on the records, and the action then
        # runs with the pinner's authority rather than the caller's.
        if self.usage == "documents_embedded" and not records.env.su:
            _debug.logic("embedded_action_elevated", action=self, records=records)
            env = eval_context["env"](su=True)
            records = records.with_env(env)
            eval_context = {
                **eval_context,
                "env": env,
                "model": eval_context["model"].with_env(env),
                "records": records or None,
                "record": records[:1] or None,
            }
        return super()._run(records, eval_context)

    def _check_access_to_run(self, records: models.Model) -> None:
        if self.usage == "documents_embedded":
            # The pinned actions are a property of the folder, so resolve
            # them once per folder rather than once per record.
            for folder_records in records.grouped("folder_id").values():
                available_sudo = (
                    self.env["ir.actions.server"]
                    .sudo()
                    .browse(
                        folder_records[:1]
                        .available_embedded_actions_ids.action_id.sudo()
                        .filtered(lambda a: a.type == "ir.actions.server")
                        .ids
                    )
                )
                frontier = available_sudo
                while frontier.child_ids:
                    next_frontier = frontier.child_ids - available_sudo
                    available_sudo |= frontier.child_ids
                    frontier = next_frontier

                if self not in available_sudo or any(
                    not d.available_embedded_actions_ids for d in folder_records
                ):
                    _debug.logic(
                        "embedded_action_refused",
                        reason="not_pinned_on_folder",
                        action=self,
                        records=folder_records,
                    )
                    raise UserError(
                        _(
                            "This action was not made available on the containing folder."
                        )
                    )

        return super()._check_access_to_run(records)
