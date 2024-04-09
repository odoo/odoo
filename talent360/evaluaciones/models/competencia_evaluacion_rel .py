from odoo import models, fields


class CompetenciaEvaluacionRel(models.Model):
    _name = "competencia.evaluacion.rel"
    _description = "Relación entre competencia y evaluaciones"

    competencia_id = fields.Many2one("competencia", string="Competencia")
    evaluacion_id = fields.Many2one("evaluacion", string="Evaluacion")
