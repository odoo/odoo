from odoo import fields, api, models


class SchoolNewsLetter(models.Model):
    _name = 'school.notice'
    name = fields.Char('Notice title', required=True)
    content = fields.Text('Notice content', required=True)