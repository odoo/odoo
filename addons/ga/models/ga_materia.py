from odoo import fields, models
class Materia(models.Model):
    _name = "ga.materia"
    _description = "GA materia"
    codigo = fields.Char(required=True)
    descripcion = fields.Text(required=True)