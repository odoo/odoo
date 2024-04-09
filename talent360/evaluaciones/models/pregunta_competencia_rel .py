from odoo import models, fields


class PreguntaCompetenciaRel(models.Model):
    _name = "pregunta.competencia.rel"
    _description = "Relación entre competencia y preguntas"

    competencia_id = fields.Many2one("competencia", string="Competencia")
    pregunta_id = fields.Many2one("pregunta", string="Pregunta")
