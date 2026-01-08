from odoo import fields, models
class Paralelo(models.Model):
    _name="ga.paralelo"
    _description="Paralelo"
    codigo=fields.Char(required=True)
    descripcion=fields.Text()
