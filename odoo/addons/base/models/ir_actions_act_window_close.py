from odoo import models


class IrActionsAct_Window_Close(models.Model):
    _name = "ir.actions.act_window_close"
    _description = "Action Window Close"
    _inherit = ["ir.actions.actions"]
    _table = "ir_act_window_close"

    def _get_keys_client_only(self) -> frozenset[str]:
        return super()._get_keys_client_only() | {"effect", "infos"}
