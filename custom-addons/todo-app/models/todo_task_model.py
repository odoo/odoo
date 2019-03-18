from odoo import fields, models

class TodoTask(models.Model):
    _name = 'todo.task' # the id that will be used throughout Odoo to refer to this model
    _description = 'To-do Task' # this field isn't mandatory
    name = fields.Char('Description', required=True) # name and active will display when the model reference from another model
    is_done = fields.Boolean('Done?')
    active = fields.Boolean('Active?', default=True)
    user_id = fields.Many2one(
    'res.users',
    string='Responsible',
    default=lambda self: self.env.user)
    team_ids = fields.Many2many('res.partner', string='Team')