from odoo import api, models


class MixinApprovalLifecycle(models.AbstractModel):
    _name = "mixin.approval.lifecycle"
    _inherit = ["mixin.approval.gate", "mixin.lifecycle"]
    _description = "Lifecycle Confirmed Through Approval"

    _approval_operations = ("action_confirm",)
    _operation_checkpoints = {"action_confirm": "_check_confirm_transition"}

    def action_confirm(self):
        self._check_confirm_allowed()
        return self._run_through_approval(
            "action_confirm", lambda records: super().action_confirm()
        )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        confirmed = records._get_confirmed_state()
        records.filtered(lambda r: r.state == confirmed)._check_confirm_transition()
        return records

    def _get_confirmed_state(self):
        return self.browse()._prepare_confirmation_values()["state"]

    def _get_check_write_guards(self):
        return [*super()._get_check_write_guards(), "_check_write_confirm_transition"]

    def _check_write_confirm_transition(self, vals):
        if "state" not in vals:
            return
        confirmed = self._get_confirmed_state()
        if vals["state"] != confirmed:
            return
        self.filtered(lambda r: r.state != confirmed)._check_confirm_transition()

    def _check_confirm_transition(self):
        if self:
            self._check_approval_admits("action_confirm")

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
