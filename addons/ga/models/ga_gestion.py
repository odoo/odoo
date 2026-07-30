from odoo import fields, models
class Gestion(models.Model):
    _name = "ga.gestion"
    _description = "GA gestion"
    codigo = fields.Char(required=True)
    descripcion = fields.Text()
    fecha_inicio = fields.Date()
    fecha_fin = fields.Date()