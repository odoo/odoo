from odoo import fields, models

class StudentLevel(models.Model):
    _name = 'student.level'
    _description = 'Student Level'
    _order = 'sequence, name'
    _rec_name = 'code'

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', translate=True, required=True)
    sequence = fields.Integer(string='Sequence', default=1)