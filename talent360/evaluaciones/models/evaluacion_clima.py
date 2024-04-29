from odoo import models, fields, api


class EvaluacionClima(models.Model):
    """
    Modelo para representar Evaluaciones de Clima Laboral.
    Hereda de "evaluacion".
    """

    _name = "evaluacion"
    _description = "Evaluaciones de Clima Laboral"

    _inherit = ["evaluacion"]

    piso_rojo = fields.Float(
        string="Piso Rojo",
        required=False,
        default=None,
    )

    techo_rojo = fields.Float(
        string="Techo Rojo",
        required=False,
        default=None,
    )

    piso_amarillo = fields.Float(
        string="Piso Amarillo",
        required=False,
        default=None,
    )

    techo_amarillo = fields.Float(
        string="Techo Amarillo",
        required=False,
        default=None,
    )

    piso_verde = fields.Float(
        string="Piso Verde",
        required=False,
        default=None,
    )

    techo_verde = fields.Float(
        string="Techo Verde",
        required=False,
        default=None,
    )

    piso_azul = fields.Float(
        string="Piso Azul",
        required=False,
        default=None,
    )

    techo_azul = fields.Float(
        string="Techo Azul",
        required=False,
        default=None,
    )

    descripcion_rojo = fields.Text(
        string="Descripción Rojo",
        required=False,
        default=None,
    )

    descripcion_amarillo = fields.Text(
        string="Descripción Amarillo",
        required=False,
        default=None,
    )

    descripcion_verde = fields.Text(
        string="Descripción Verde",
        required=False,
        default=None,
    )

    descripcion_azul = fields.Text(
        string="Descripción Azul",
        required=False,
        default=None,
    )
