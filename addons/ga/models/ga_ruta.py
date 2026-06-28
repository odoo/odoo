from odoo import fields, models
class Ruta(models.Model):
    _name="ga.ruta"
    _description="Ruta"
    codigo=fields.Char(required=True)
    descripcion=fields.Text()
    hora_inicio=fields.Datetime(required=True)
