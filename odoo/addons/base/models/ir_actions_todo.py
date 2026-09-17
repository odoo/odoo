from typing import Any, Self

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class IrActionsTodo(models.Model):
    _name = "ir.actions.todo"
    _description = "Configuration Wizards"
    _rec_name = "action_id"
    _order = "sequence, id"
    _allow_sudo_commands = False

    name = fields.Char()
    sequence = fields.Integer(default=10)
    action_id = fields.Many2one(
        comodel_name="ir.actions.actions",
        index=True,
        required=True,
        ondelete="cascade",
    )
    state = fields.Selection(
        selection=[("open", "To Do"), ("done", "Done")],
        string="Status",
        default="open",
        required=True,
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        todos = super().create(vals_list)
        _debug.lifecycle("create", count=len(todos))
        todos._close_other_open_todos()
        return todos

    def write(self, vals: dict[str, Any]) -> bool:
        res = super().write(vals)
        _debug.lifecycle("write", count=len(self), fields=list(vals))
        if vals.get("state") == "open":
            self._close_other_open_todos()
        return res

    def unlink(self) -> bool:
        todos = self
        try:
            todo_open_menu = self.env.ref("base.open_menu")
            default_action = self.env.ref("base.action_client_base_menu")
        except ValueError:
            pass
        else:
            if todo_open_menu in todos:
                _debug.logic("unlink_menu_todo_kept", todo=todo_open_menu.id)
                todo_open_menu.action_id = default_action.id
                todos -= todo_open_menu
        _debug.lifecycle("unlink", requested=len(self), count=len(todos))
        return super(IrActionsTodo, todos).unlink()

    def _close_other_open_todos(self) -> None:
        keep = self.filtered(lambda todo: todo.state == "open").sorted()[:1]
        if not keep:
            _debug.logic("close_other_todos_skipped", reason="none_open")
            return
        others = self.search([("state", "=", "open"), ("id", "not in", keep.ids)])
        _debug.lifecycle("close_other_todos", keep=keep.id, closed=others.ids)
        others.write({"state": "done"})

    def action_launch(self) -> dict[str, Any]:
        self.check_singleton()
        self.state = "done"

        action = self.action_id._get_concrete()
        _debug.lifecycle(
            "todo_launched", todo=self.id, action=action.id, type=action._name
        )
        result = action._get_action_dict()
        if action._name != "ir.actions.act_window":
            _debug.logic("todo_launch_passthrough", todo=self.id, type=action._name)
            return result

        ctx = action._eval_action_context(result.get("context"))
        if ctx.get("res_id"):
            _debug.logic("todo_launch_res_id", todo=self.id, res_id=ctx["res_id"])
            result["res_id"] = ctx.pop("res_id")
        ctx["disable_log"] = True
        result["context"] = ctx
        return result

    def action_open(self) -> bool:
        return self.write({"state": "open"})
