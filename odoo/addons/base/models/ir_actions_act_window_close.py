from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class IrActionsAct_Window_Close(models.Model):
    _name = "ir.actions.act_window_close"
    _description = "Action Window Close"
    _inherit = ["ir.actions.actions"]
    _table = "ir_actions"
    _allow_sudo_commands = False

    type = fields.Char(default="ir.actions.act_window_close")

    def _get_keys_client_only(self) -> frozenset[str]:
        keys = super()._get_keys_client_only() | {
            "effect",
            "infos",
        }
        _debug.logic("client_only_keys", type=self._name, count=len(keys))
        return keys
