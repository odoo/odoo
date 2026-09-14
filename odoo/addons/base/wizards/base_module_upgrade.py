from typing import Any, Self

import odoo
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

from odoo.addons.base.models.ir_module import assert_log_admin_access
from odoo.addons.base.models.ir_ui_view_base import attach_ir

_debug = DebugLog(__name__)


class BaseModuleUpgrade(models.TransientModel):
    _name = "base.module.upgrade"
    _description = "Upgrade Module"

    @api.model
    def _get_pending_modules(self) -> Self:
        states = ["to upgrade", "to remove", "to install"]
        return self.env["ir.module.module"].search([("state", "in", states)])

    @api.model
    def _default_module_info(self) -> str:
        return "\n".join(
            f"{mod.name}: {mod.state}" for mod in self._get_pending_modules()
        )

    module_info = fields.Text(
        string="Apps to Update",
        default=_default_module_info,
        readonly=True,
    )

    @api.model
    def get_view(
        self,
        view_id: int | None = None,
        view_type: str = "form",
        **options: Any,
    ) -> dict[str, Any]:
        res = super().get_view(view_id, view_type, **options)
        if view_type != "form":
            return res

        if not self._get_pending_modules():
            res["arch"] = """<form string="Upgrade Completed">
                                <separator string="Upgrade Completed" colspan="4"/>
                                <footer>
                                    <button name="config" string="Start Configuration" type="object" class="btn-primary" data-hotkey="q"/>
                                    <button special="cancel" data-hotkey="x" string="Close" class="btn-secondary"/>
                                </footer>
                             </form>"""
            attach_ir(res)

        return res

    def upgrade_module_cancel(self) -> dict[str, str]:
        _debug.lifecycle("upgrade_cancelled", uid=self.env.uid)
        self.env["ir.module.module"].button_reset_state()
        return {"type": "ir.actions.act_window_close"}

    @assert_log_admin_access
    def upgrade_module(self) -> dict[str, str]:
        Module = self.env["ir.module.module"]

        mods = Module.search([("state", "in", ["to upgrade", "to install"])])
        if mods:
            query = """ SELECT d.name
                        FROM ir_module_module m
                        JOIN ir_module_module_dependency d ON (m.id = d.module_id)
                        LEFT JOIN ir_module_module m2 ON (d.name = m2.name)
                        WHERE m.id = any(%s) and (m2.state IS NULL or m2.state = %s) """
            self.env.cr.execute(query, (mods.ids, "uninstalled"))
            unmet_packages = [row[0] for row in self.env.cr.fetchall()]
            if unmet_packages:
                _debug.logic(
                    "upgrade_unmet_dependencies",
                    modules=len(mods),
                    unmet=unmet_packages,
                )
                raise UserError(
                    self.env._(
                        "The following modules are not installed or unknown: %s",
                        "\n\n" + "\n".join(unmet_packages),
                    )
                )

        _debug.pipeline("upgrade_planned", modules=mods.mapped("name"))
        self.env.cr.commit()
        with _debug.perf("registry_reload", db=self.env.cr.dbname, modules=len(mods)):
            odoo.modules.registry.Registry.new(self.env.cr.dbname, update_module=True)
        self.env.cr.reset()

        return {"type": "ir.actions.act_window_close"}

    def config(self) -> dict[str, Any]:
        return self.env["res.config"]._next_todo_action()
