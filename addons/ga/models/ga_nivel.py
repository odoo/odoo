from odoo import fields, models
class Nivel(models.Model):
    _name = "ga.nivel"
    _description = "GA nivel"
    codigo = fields.Char()
    descripcion = fields.Text()