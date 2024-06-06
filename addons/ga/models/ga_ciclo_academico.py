from odoo import fields, models
class CicloAcademico(models.Model):
    _name = "ga.ciclo.academico"
    _description = "GA ciclo academico"
    codigo = fields.Char(required = True)
    descripcion = fields.Text()
    fecha_inicio = fields.Date()
    fecha_fin = fields.Date()
    gestion_id = fields.Many2one("ga.gestion", string="Gestion",required=True)