from odoo import api, fields, models
from odoo.fields import Command

SYNC_CONTEXT_KEY = "approval_binding_syncing"


class ApprovalBinding(models.Model):
    _inherit = "approval.binding"

    reset_domain = fields.Char(
        string="Reset When",
        help="Domain on the gated model. When a covered record comes to match it, "
        "the approval that covered the record is reset to draft, so the next call "
        "asks again -- the way web_studio resets its approvals when a sale order, "
        "invoice or purchase order returns to draft, for any model and condition. "
        "It fires on the transition INTO the condition only, so an approval given "
        "while the record already matches is not wiped by the next edit.",
    )
    reset_automation_id = fields.Many2one(
        comodel_name="automation.rule",
        copy=False,
        readonly=True,
        ondelete="set null",
        help="The automation rule this binding keeps in step with Reset When.",
    )

    @api.constrains("model_id", "reset_domain")
    def _check_reset_domain(self) -> None:
        for binding in self:
            model = self.env.get(binding.model_id.model)
            if model is not None and binding.reset_domain:
                binding._check_domain_against_model(model, "reset_domain")

    @api.model_create_multi
    def create(self, vals_list):
        bindings = super().create(vals_list)
        bindings._sync_reset_automation()
        return bindings

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get(SYNC_CONTEXT_KEY):
            self._sync_reset_automation()
        return result

    def unlink(self):
        automations = self.sudo().reset_automation_id
        result = super().unlink()
        automations.unlink()
        return result

    def _sync_reset_automation(self) -> None:
        """Keep one managed automation rule per binding that has a Reset When.

        The rule fires on a record's transition INTO the condition: its
        pre-update filter is the condition inverted. Without that, an approval
        given while the record already matches -- a sale order approved in draft,
        then edited before confirming -- would be wiped by the next unrelated
        write.

        After creation only the name, the two filters and the trigger fields are
        written. Never `trigger`: `_compute_filter_pre_domain` clears the pre-update
        filter for every trigger but one whenever it moves. And never `model_id`:
        writing it, even unchanged, recomputes `trigger` to nothing and the row
        fails its NOT NULL constraint -- so a binding whose model changed gets a new
        rule rather than an edited one.
        """
        for binding in self.sudo():
            automation = binding.reset_automation_id
            if not binding.reset_domain or not binding.active:
                if automation:
                    binding.with_context(**{SYNC_CONTEXT_KEY: True}).write(
                        {"reset_automation_id": False}
                    )
                    automation.unlink()
                continue
            domain = binding._parse_domain("reset_domain")
            vals = {
                "name": self.env._("Approval reset: %(binding)s", binding=binding.name),
                "filter_domain": binding.reset_domain,
                "filter_pre_domain": repr(list(~domain)),
                "trigger_field_ids": [
                    Command.set(binding._get_reset_field_ids(domain))
                ],
            }
            if automation and automation.model_id == binding.model_id:
                automation.write(vals)
                continue
            if automation:
                automation.unlink()
            automation = self.env["automation.rule"].create(
                {
                    **vals,
                    "model_id": binding.model_id.id,
                    "trigger": "on_create_or_write",
                    "action_server_ids": [
                        Command.create(
                            {
                                "name": self.env._(
                                    "Reset the approvals of %(binding)s",
                                    binding=binding.name,
                                ),
                                "model_id": binding.model_id.id,
                                "state": "code",
                                "usage": "automation",
                                "code": "env['approval.binding'].browse("
                                f"{binding.id})._reset_coverage(records)",
                            }
                        )
                    ],
                }
            )
            binding.with_context(**{SYNC_CONTEXT_KEY: True}).write(
                {"reset_automation_id": automation.id}
            )

    def _get_reset_field_ids(self, domain) -> list[int]:
        self.check_singleton()
        Fields = self.env["ir.model.fields"]
        names = {path.split(".", 1)[0] for path in self._domain_field_paths(domain)}
        return [Fields._get(self.model_name, name).id for name in sorted(names)]
