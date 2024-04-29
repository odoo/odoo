from odoo import models, fields, api
from odoo.exceptions import ValidationError


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
        default=0,
        store=False,
    )

    techo_rojo = fields.Float(
        string="Techo Rojo",
        required=True,
        default=1,
    )

    techo_amarillo = fields.Float(
        string="Techo Amarillo",
        required=True,
        default=2,
    )

    techo_verde = fields.Float(
        string="Techo Verde",
        required=True,
        default=3,
    )

    techo_azul = fields.Float(
        string="Techo Azul",
        required=True,
        default=4,
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

    @api.constrains("techo_rojo", "techo_amarillo", "techo_verde", "techo_azul")
    def _check_techos(self):
        """
        Valida que los techos sean mayores a 0 y estén en orden ascendente.
        """
        techos = [
            ('rojo', self.techo_rojo),
            ('amarillo', self.techo_amarillo),
            ('verde', self.techo_verde),
            ('azul', self.techo_azul),
        ]

        for techo in techos:
            if techo[1] <= 0:
                raise ValidationError(
                    (f"El techo {techo[0]} debe ser mayor a 0"))

        for i in range(len(techos) - 1):
            if techos[i][1] >= techos[i + 1][1]:
                raise ValidationError(
                    ("Los techos deben ser en orden ascendente"))
