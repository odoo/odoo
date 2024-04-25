from odoo import models, fields, api


class Evaluacion360(models.Model):
    """
    Modelo para representar Evaluaciones 360.
    Hereda de "evaluacion".
    """

    _name = "evaluacion"
    _description = "Evaluaciones 360"

    _inherit = ["evaluacion"]

    preguntas_360_ids = fields.Many2many(
        "pregunta",
        compute="_compute_preguntas_360_ids",
        string="Preguntas 360",
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
