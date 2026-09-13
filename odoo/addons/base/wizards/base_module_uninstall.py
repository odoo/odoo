from typing import Any, Self

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class BaseModuleUninstall(models.TransientModel):
    _name = "base.module.uninstall"
    _description = "Module Uninstall"

    show_all = fields.Boolean()
    module_ids = fields.Many2many(
        comodel_name="ir.module.module",
        string="Module(s)",
        readonly=True,
        required=True,
        domain=[("state", "in", ["installed", "to upgrade", "to install"])],
        ondelete="cascade",
    )
    impacted_module_ids = fields.Many2many(
        comodel_name="ir.module.module",
        string="Impacted modules",
        compute="_compute_impacted_module_ids",
    )
    model_ids = fields.Many2many(
        comodel_name="ir.model",
        string="Impacted data models",
        compute="_compute_model_ids",
    )

    def _get_modules(self) -> Self:
        return self.module_ids.downstream_dependencies(self.module_ids)

    @api.depends("module_ids", "show_all")
    def _compute_impacted_module_ids(self) -> None:
        for wizard in self:
            modules = wizard._get_modules().sorted(
                lambda m: (not m.application, m.sequence)
            )
            wizard.impacted_module_ids = (
                modules if wizard.show_all else wizard._get_modules_to_display(modules)
            )
            _debug.pipeline(
                "uninstall_impact",
                modules=wizard.module_ids.mapped("name"),
                downstream=len(modules),
                shown=len(wizard.impacted_module_ids),
            )

    @api.model
    def _get_modules_to_display(self, modules: Self) -> Self:
        return modules.filtered("application")

    def _get_models(self) -> Any:
        return self.env["ir.model"].search([("transient", "=", False)])

    @api.depends("module_ids")
    def _compute_model_ids(self) -> None:
        ir_models = self._get_models()
        ir_models_xids = ir_models._get_external_ids()
        for wizard in self:
            if wizard.module_ids:
                module_names = set(wizard._get_modules().mapped("name"))

                def lost(model, _module_names=module_names):
                    xids = ir_models_xids.get(model.id, ())
                    return xids and all(
                        xid.split(".")[0] in _module_names for xid in xids
                    )

                wizard.model_ids = ir_models.filtered(lost).sorted("name")
                _debug.pipeline(
                    "uninstall_lost_models",
                    modules=len(module_names),
                    candidates=len(ir_models),
                    lost=len(wizard.model_ids),
                )
            else:
                wizard.model_ids = False

    @api.onchange("module_ids")
    def _onchange_module_ids(self) -> None:
        if self.module_ids and not any(m.application for m in self.module_ids):
            self.show_all = True

    def action_uninstall(self) -> dict[str, Any]:
        modules = self.module_ids
        _debug.lifecycle("wizard_uninstall", modules=modules.mapped("name"))
        return modules.button_immediate_uninstall()
