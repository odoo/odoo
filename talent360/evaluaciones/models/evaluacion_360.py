from odoo import models, fields, api


class Evaluacion360(models.Model):
    """
    Modelo para representar Evaluaciones 360.
    Hereda de "evaluacion".

    :param _name (str): Nombre del modelo en Odoo
    :param _description (str): Descripción del modelo en Odoo
    :param preguntas_360_ids (list): Lista de preguntas 360 asociadas a la evaluación
    :param tipo_competencia (str): Tipo de competencia a evaluar
    """

    _name = "evaluacion"
    _description = "Evaluaciones 360"

    _inherit = ["evaluacion"]

    preguntas_360_ids = fields.Many2many(
        "pregunta",
        compute="_compute_preguntas_360_ids",
        string="Resumen de preguntas",
        store=False,
    )

    tipo_competencia = fields.Selection(
        [
            ("90", "90 Grados"),
            ("180", "180 Grados"),
            ("270", "270 Grados"),
            ("360", "360 Grados"),
        ],
        required=False,
        default=None,
    )

    @api.depends("competencia_ids")
    def _compute_preguntas_360_ids(self):
        """
        Método que calcula las preguntas 360 de la evaluación.
        """
        for evaluacion in self:
            preguntas_360 = evaluacion.competencia_ids.mapped("pregunta_ids")
            evaluacion.preguntas_360_ids = preguntas_360
