from odoo import fields, models

class TodoTask(models.Model):
    _name = 'todo.task'
    _description = 'To-do Task'
    name = fields.Char('Description', required=True)
    is_done = fields.Boolean('Done?')
    active = fields.Boolean('Active?', default=True)
    user_id = fields.Many2one(
    'res.users',
    string='Responsible',
    default=lambda self: self.env.user)
    team_ids = fields.Many2many('res.partner', string='Team')