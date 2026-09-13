from typing import Any

from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class BaseModuleUpdate(models.TransientModel):
    _name = "base.module.update"
    _description = "Update Module"

    updated = fields.Integer(
        string="Number of modules updated",
        readonly=True,
    )
    added = fields.Integer(
        string="Number of modules added",
        readonly=True,
    )
    state = fields.Selection(
        selection=[("init", "init"), ("done", "done")],
        string="Status",
        default="init",
        readonly=True,
    )

    def update_module(self) -> bool:
        for this in self:
            with _debug.perf("update_list", cr=self.env.cr) as span:
                updated, added = self.env["ir.module.module"].update_list()
                span.set(updated=updated, added=added)
            this.write({"updated": updated, "added": added, "state": "done"})
        return False

    def action_module_open(self) -> dict[str, Any]:
        return {
            "domain": [],
            "name": self.env._("Modules"),
            "view_mode": "list,form",
            "res_model": "ir.module.module",
            "view_id": False,
            "type": "ir.actions.act_window",
        }
