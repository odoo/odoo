from odoo import fields, api, models


class SchoolNewsLetter(models.Model):
    _name = 'school.newsletter'
    name = fields.Char('News Letter Title', required=True)
    content = fields.Html('News Letter Content', required=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('ready', 'Ready')],
                             default='draft')
