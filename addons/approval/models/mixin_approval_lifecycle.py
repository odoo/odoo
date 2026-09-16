from odoo import models


class MixinApprovalLifecycle(models.AbstractModel):
    _name = "mixin.approval.lifecycle"
    _inherit = ["mixin.approval.gate", "mixin.lifecycle"]
    _description = "Lifecycle Confirmed Through Approval"

    _approval_operations = ("action_confirm",)

    def action_confirm(self):
        self._check_confirm_allowed()
        return self._run_through_approval(
            "action_confirm", lambda records: super().action_confirm()
        )

    def _is_operation_run_on_approval(self, operation):
        self.check_singleton()
        return self.state == "draft"

    def action_cancel(self):
        result = super().action_cancel()
        self._refuse_pending_approval()
        return result

    def action_draft(self):
        result = super().action_draft()
        self._clear_refused_approval_link()
        return result
