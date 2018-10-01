from odoo import fields, models


class Usered(models.Model):
    _name = 'test_convert.usered'
    _description = "z test model ignore"

    name = fields.Char()
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    tz = fields.Char(default=lambda self: self.env.context.get('tz') or self.env.user.tz)
