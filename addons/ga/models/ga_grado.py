from odoo import fields, models
class Grado(models.Model):
    _name = "ga.grado"
    _description = "GA grado"
    codigo = fields.Char(required = True)
    descripcion = fields.Text()
    nivel_id = fields.Many2one("ga.nivel", string="Nivel",required=True)