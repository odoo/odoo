from typing import Any

from odoo import fields, models


class WizardIrModelMenuCreate(models.TransientModel):
    _name = "wizard.ir.model.menu.create"
    _description = "Create Menu Wizard"

    menu_id = fields.Many2one(
        "ir.ui.menu", string="Parent Menu", required=True, ondelete="cascade"
    )
    name = fields.Char(string="Menu Name", required=True)

    def menu_create(self) -> dict[str, Any]:
        for menu in self:
            model_id = self.env.context.get("model_id")
            if not model_id:
                continue
            model = self.env["ir.model"].browse(model_id)
            vals = {
                "name": menu.name,
                "res_model": model.model,
                "view_mode": "list,form",
            }
            action = self.env["ir.actions.act_window"].create(vals)
            self.env["ir.ui.menu"].create(
                {
                    "name": menu.name,
                    "parent_id": menu.menu_id.id,
                    "action": f"ir.actions.act_window,{action.id}",
                }
            )
        return {"type": "ir.actions.act_window_close"}
