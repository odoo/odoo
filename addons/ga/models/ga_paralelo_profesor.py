from odoo import fields, models
class ParaleloProfesor(models.Model):
    _name="ga.paralelo.profesor"
    _description="ParaleloProfesor"
    profesor_id = fields.Many2one("hr.employee",required=True)
    aula_id = fields.Many2one("ga.aula", required=True)
    paralelo_id = fields.Many2one("ga.paralelo", required=True)
    plan_estudio_id=fields.Many2one("ga.plan.estudio", required=True)