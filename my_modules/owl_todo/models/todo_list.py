from odoo import fields, models

class EstateProperty(models.Model):
    _name = "owl.todo.list"
    _description = "Owl Todo List"

    name = fields.Char("Task Name")
    color = fields.Char("")
    completed = fields.Boolean()