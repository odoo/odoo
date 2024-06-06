from odoo import fields, models
class ParaleloProfesor(models.Model):
    _name="ga.paralelo.profesor"
    _description="ParaleloProfesor"
    profesor_id = fields.Many2one("ga.profesor", string="Profesor", required=True)
    aula_id = fields.Many2one("ga.aula", string="Aula", required=True)
    paralelo_id = fields.Many2one("ga.paralelo", string="Paralelo", required=True)
    plan_estudio_id=fields.Many2one("ga.plan.estudio", string="Plan Estudio", required=True)