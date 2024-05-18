from odoo import models, fields


class PreguntaEvaluacionRel(models.Model):
    """
    Modelo para representar la relación entre evaluaciones y preguntas

    :param _name (str): Nombre del modelo en Odoo
    :param _description (str): Descripción del modelo en Odoo
    :param evaluacion_id (int): Identificador de la evaluación
    :param pregunta_id (int): Identificador de la pregunta
    """

    _name = "pregunta.evaluacion.rel"
    _description = "Relación entre evaluacion y preguntas"

    evaluacion_id = fields.Many2one("evaluacion", string="Evaluacion")
    pregunta_id = fields.Many2one("pregunta", string="Pregunta")
