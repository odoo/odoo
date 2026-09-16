from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class IrActionsAct_Url(models.Model):
    _name = "ir.actions.act_url"
    _description = "Action URL"
    _table = "ir_act_url"
    _inherit = ["ir.actions.actions"]
    _order = "name, id"
    _allow_sudo_commands = False

    type = fields.Char(default="ir.actions.act_url")
    url = fields.Text(
        string="Action URL",
        required=True,
    )
    target = fields.Selection(
        selection=[
            ("new", "New Window"),
            ("self", "This Window"),
            ("download", "Download"),
        ],
        string="Action Target",
        default="new",
        required=True,
    )

    def _get_fields_readable(self) -> frozenset[str]:
        readable = super()._get_fields_readable() | {
            "target",
            "url",
        }
        _debug.logic("readable_fields", type=self._name, count=len(readable))
        return readable

    def _get_keys_client_only(self) -> frozenset[str]:
        keys = super()._get_keys_client_only() | {"close"}
        _debug.logic("client_only_keys", type=self._name, count=len(keys))
        return keys
