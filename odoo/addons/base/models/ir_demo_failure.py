from typing import Any

from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class IrDemo_Failure(models.TransientModel):
    _name = "ir.demo_failure"
    _description = "Demo failure"

    module_id = fields.Many2one("ir.module.module", required=True)
    error = fields.Text()
    wizard_id = fields.Many2one("ir.demo_failure.wizard")


class IrDemo_FailureWizard(models.TransientModel):
    _name = "ir.demo_failure.wizard"
    _description = "Demo Failure wizard"

    failure_ids = fields.One2many(
        "ir.demo_failure",
        "wizard_id",
        readonly=True,
        string="Demo Installation Failures",
    )
    failures_count = fields.Count("failure_ids")

    def done(self) -> dict[str, Any]:
        _debug.lifecycle("demo_failures_acknowledged", failures=self.failures_count)
        return self.env["ir.module.module"]._next_todo_action()
