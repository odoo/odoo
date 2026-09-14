from typing import Any

from odoo import SUPERUSER_ID, _, api, fields, models


class ResUsersDeletion(models.Model):
    _name = "res.users.deletion"
    _inherit = ["res.users.deletion", "mixin.mail.thread", "mixin.approval"]

    state = fields.Selection(
        selection_add=[("refused", "Refused")],
        ondelete={"refused": "set default"},
    )

    @api.model_create_multi
    def create(self, vals_list: list[dict[str, Any]]):
        requests = super().create(vals_list)
        if self.env.context.get("approval_skip"):
            return requests
        for deletion in requests.with_user(SUPERUSER_ID):
            if deletion.approval_required and not deletion.approval_request_id:
                deletion.action_create_approval_request()
        return requests

    @api.model
    def _get_domain_deletion_due(self) -> list:
        return super()._get_domain_deletion_due() + [
            ("approval_state", "in", ("approved", False))
        ]

    def _get_domain_approval_category(self) -> list[Any]:
        category = self.env.ref(
            "approval_res_users_deletion.approval_category_account_deletion",
            raise_if_not_found=False,
        )
        return [("id", "=", category.id)] if category else []

    def _get_fields_approval_protected(self) -> list[str]:
        return ["user_id"]

    def _get_approval_request_name(self) -> str:
        return _("Account deletion of %s", self.user_id.name or self.user_id_int)

    def _get_approval_reason_html(self) -> str:
        return _(
            "Portal user %(name)s (#%(id)s) asked for their account and its "
            "personal data to be deleted.",
            name=self.user_id.name or "",
            id=self.user_id_int,
        )

    def _prepare_approval_request_values(self, category: Any) -> dict[str, Any]:
        vals = super()._prepare_approval_request_values(category)
        if self.user_id.partner_id:
            vals["partner_id"] = self.user_id.partner_id.id
        vals["request_owner_id"] = self.env.ref("base.user_root").id
        return vals

    def _on_approval_refused(self) -> None:
        super()._on_approval_refused()
        self.state = "refused"

    def _on_approval_cancelled(self) -> None:
        super()._on_approval_cancelled()
        self.state = "refused"
