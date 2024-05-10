from odoo import models, fields


class CompetenciaEvaluacionRel(models.Model):
    """
    Modelo para representar la relación entre competencias y evaluaciones
    
    :param _name (str): Nombre del modelo en Odoo
    :param _description (str): Descripción del modelo en Odoo
    :param competencia_id (int): Identificador de la competencia
    :param evaluacion_id (int): Identificador de la evaluación
    """
    
    _name = "competencia.evaluacion.rel"
    _description = "Relación entre competencia y evaluaciones"

    competencia_id = fields.Many2one("competencia", string="Competencia")
    evaluacion_id = fields.Many2one("evaluacion", string="Evaluacion")
