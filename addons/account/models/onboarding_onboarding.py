from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class OnboardingOnboarding(models.Model):
    _inherit = "onboarding.onboarding"

    @api.model
    @_debug.perf.timed
    def action_close_panel_account_invoice(self):
        _debug.lifecycle("action_close_panel_account_invoice", records=self)
        self.action_close_panel("account.onboarding_onboarding_account_invoice")

    @_debug.perf.timed
    def _prepare_rendering_values(self):
        self.check_singleton()
        if self == self.env.ref(
            "account.onboarding_onboarding_account_invoice", raise_if_not_found=False
        ):
            step = self.env.ref(
                "account.onboarding_onboarding_step_create_invoice",
                raise_if_not_found=False,
            )
            if step and step.current_step_state == "not_done":
                _debug.logic("invoice_step_pending", onboarding=self, step=step)
                if self.env["account.move"].search_count(
                    [
                        ("company_id", "=", self.env.company.id),
                        ("move_type", "=", "out_invoice"),
                    ],
                    limit=1,
                ):
                    _debug.logic("invoice_step_marked_done", step=step)
                    step.action_set_just_done()
        return super()._prepare_rendering_values()

    @api.model
    @_debug.perf.timed
    def action_close_panel_account_dashboard(self):
        _debug.lifecycle("action_close_panel_account_dashboard", records=self)
        self.action_close_panel("account.onboarding_onboarding_account_dashboard")
