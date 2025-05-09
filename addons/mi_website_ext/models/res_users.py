from odoo import models, fields

class Users(models.Model):
    _inherit = 'res.users'

    bio = fields.Text(string='Biografía')
