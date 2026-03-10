from odoo import models, fields


class ToDoAction(models.Model):
    _name = "todo.action"
    _description = "To Do Actions"
    _order = "sequence"

    name = fields.Char(string="Title")
    action_line_ids = fields.One2many(
        "todo.action.line",
        "action_id",
        copy=True,
        bypass_search_access=True,
        help="Set Action Line For To Do Actions.",
    )
    layout_id = fields.Many2one(
        "dashboard.chart", ondelete="cascade", index=True, copy=False
    )
    sequence = fields.Integer("Sequence", default=10)


class ToDoActionsLine(models.Model):
    _name = "todo.action.line"
    _description = "To Do Actions Line"
    _order = "sequence"

    name = fields.Char(string="Task")
    active_record = fields.Boolean(
        string="Active", default=True, help="Set Action Line For To Do Actions."
    )
    action_id = fields.Many2one(
        "todo.action", ondelete="cascade", index=True, copy=False
    )
    sequence = fields.Integer(default=0)
