from odoo import api, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class IrEmbeddedActions(models.Model):
    _inherit = "ir.embedded.actions"

    @api.model_create_multi
    def create(self, vals_list: list[dict]) -> IrEmbeddedActions:
        records = super().create(vals_list)
        records._check_documents_can_pin()
        return records

    def write(self, vals: dict) -> bool:
        self._check_documents_can_pin()
        ret = super().write(vals)
        self._check_documents_can_pin()
        return ret

    def _check_documents_can_pin(self) -> None:
        to_check = self.filtered(
            lambda a: (
                a.parent_action_id
                == self.env.ref("document.document_action", raise_if_not_found=False)
                and a.parent_res_model == "document.document"
            ),
        )
        if to_check:
            folders = self.env["document.document"].browse(
                to_check.mapped("parent_res_id")
            )
            _debug.logic("pin_access_checked", embedded=to_check, folders=folders)
            folders.check_access("write")

    @api.model
    def _get_domain_documents_embed_base(self) -> list:
        return [
            ("parent_action_id", "=", self.env.ref("document.document_action").id),
            ("action_id.type", "=", "ir.actions.server"),
            ("parent_res_model", "=", "document.document"),
        ]

    @api.autovacuum
    def _gc_documents_obsolete(self) -> tuple[int, bool]:
        embeddable = self.env["ir.actions.server"]._search(
            self.env["document.document"]._get_domain_embeddable_server_action(
                restrict_to_user_groups=False
            )
        )
        limit = 1000
        obsolete = self.search(
            Domain.AND(
                [
                    self._get_domain_documents_embed_base(),
                    [("action_id", "not in", embeddable)],
                ]
            ),
            limit=limit,
        )
        removed = len(obsolete)
        _debug.lifecycle("embedded_actions_gc", removed=removed)
        obsolete.unlink()
        return removed, removed == limit
