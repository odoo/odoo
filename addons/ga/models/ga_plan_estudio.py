from odoo import fields, models
class PlanEstudio(models.Model):
    _name = "ga.plan.estudio"
    _description = "GA plan estudio"
    horas = fields.Integer()
    materia_id = fields.Many2one("ga.materia", required=True)
    gestion_id = fields.Many2one("ga.gestion",  required=True)
    nivel_id = fields.Many2one("ga.nivel", required=True)