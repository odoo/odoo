from odoo import fields, models
class Aula(models.Model):
    _name="ga.aula"
    _description="Aula"
    codigo=fields.Char(required=True)
    descripcion=fields.Text()
    capacidad=fields.Integer()