from odoo import models, fields


class PreguntaEvaluacionRel(models.Model):
    _name = "pregunta.evaluacion.rel"
    _description = "Relación entre evaluacion y preguntas"

    evaluacion_id = fields.Many2one("evaluacion", string="Evaluacion")
    pregunta_id = fields.Many2one("pregunta", string="Pregunta")