from odoo import fields, models
class PlanEstudio(models.Model):
    _name = "ga.plan.estudio"
    _description = "GA plan estudio"
    horas = fields.Integer()
    materia_id = fields.Many2one("ga.materia", String="Plan estudio", required=True)
    gestion_id = fields.Many2one("ga.gestion", String="Gestion", required=True)
    nivel_id = fields.Many2one("ga.nivel", string="Ciclo Academico",required=True)