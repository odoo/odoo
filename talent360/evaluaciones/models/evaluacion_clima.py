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
        required=False,
        default=0,
        store=False,
    )

    techo_rojo = fields.Float(
        required=True,
        default=50,
    )

    techo_naranja = fields.Float(
        required=True,
        default=70,
    )

    techo_amarillo = fields.Float(
        required=True,
        default=80,
    )

    techo_verde = fields.Float(
        required=True,
        default=90,
    )

    techo_azul = fields.Float(
        required=True,
        default=100,
    )

    descripcion_rojo = fields.Text(
        required=False,
        default="Deficiente",
    )

    descripcion_naranja = fields.Text(
        required=False,
        default="Regular",
    )

    descripcion_amarillo = fields.Text(
        required=False,
        default="Marginal",
    )

    descripcion_verde = fields.Text(
        required=False,
        default="Suficiente",
    )

    descripcion_azul = fields.Text(
        required=False,
        default="Superior",
    )

    @api.constrains("techo_rojo", "techo_naranja", "techo_amarillo", "techo_verde", "techo_azul")
    def _check_techos(self):
        """
        Valida que los techos sean mayores a 0 y estén en orden ascendente.
        """
        techos = [
            ('rojo', self.techo_rojo),
            ('naranja', self.techo_naranja),
            ('amarillo', self.techo_amarillo),
            ('verde', self.techo_verde),
            ('azul', self.techo_azul),
        ]

        for techo in techos:
            if techo[1] <= 0:
                raise ValidationError(
                    (f"El nivel {techo[0]} debe ser mayor a 0"))

        for i in range(len(techos) - 1):
            if techos[i][1] >= techos[i + 1][1]:
                raise ValidationError(
                    ("Los niveles deben ser en orden ascendente"))
