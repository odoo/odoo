from odoo import models, fields

class TaskManager(models.Model):
    _name = "task.manager"
    _description = "Task Manager"

    name = fields.Char("Task", required=True)
    is_done = fields.Boolean("Done", default=False)
