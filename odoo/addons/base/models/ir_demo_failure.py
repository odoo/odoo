from typing import Any

from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class IrDemo_Failure(models.TransientModel):
    _name = "ir.demo_failure"
    _description = "Demo failure"

    module_id = fields.Many2one(
        comodel_name="ir.module.module",
        required=True,
    )
    error = fields.Text()
    wizard_id = fields.Many2one(comodel_name="ir.demo_failure.wizard")


class IrDemo_FailureWizard(models.TransientModel):
    _name = "ir.demo_failure.wizard"
    _description = "Demo Failure wizard"

    failure_ids = fields.One2many(
        comodel_name="ir.demo_failure",
        inverse_name="wizard_id",
        string="Demo Installation Failures",
        readonly=True,
    )
    failures_count = fields.Count(count_of="failure_ids")

    def done(self) -> dict[str, Any]:
        _debug.lifecycle("demo_failures_acknowledged", failures=self.failures_count)
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "demo_failures_modules",
                modules=sorted(self.failure_ids.mapped("module_id.name")),
            )
        return self.env["ir.module.module"]._next_todo_action()
