from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EvaluacionClima(models.Model):
    """
    Modelo para representar Evaluaciones de Clima Laboral.
    Hereda de "evaluacion".

    :param _name (str): Nombre del modelo en Odoo
    :param _description (str): Descripción del modelo en Odoo
    :param piso_rojo (float): Piso del nivel rojo
    :param techo_rojo (float): Techo del nivel rojo
    :param techo_naranja (float): Techo del nivel naranja
    :param techo_amarillo (float): Techo del nivel amarillo
    :param techo_verde (float): Techo del nivel verd
    :param techo_azul (float): Techo del nivel azul
    :param descripcion_rojo (str): Descripción del nivel rojo
    :param descripcion_naranja (str): Descripción del nivel naranja
    :param descripcion_amarillo (str): Descripción del nivel amarillo
    :param descripcion_verde (str): Descripción del nivel verde
    :param descripcion_azul (str): Descripción del nivel azul
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

    @api.constrains(
        "techo_rojo", "techo_naranja", "techo_amarillo", "techo_verde", "techo_azul"
    )
    def _checar_techos(self):
        """
        Se valida que los techos sean mayores a 0 y estén en orden ascendente.
        """
        techos = [
            ("rojo", self.techo_rojo),
            ("naranja", self.techo_naranja),
            ("amarillo", self.techo_amarillo),
            ("verde", self.techo_verde),
            ("azul", self.techo_azul),
        ]

        for techo in techos:
            if techo[1] <= 0:
                raise ValidationError(_((f"El nivel {techo[0]} debe ser mayor a 0")))
            elif techo[1] > 100:
                raise ValidationError((f"El nivel {techo[0]} no puede ser mayor a 100"))

        for i in range(len(techos) - 1):
            for j in range(i + 1, len(techos)):
                if techos[i][1] > techos[j][1]:
                    raise ValidationError(
                        _((f"Los niveles de techo deben estar en orden ascendente"))
                    )
                if techos[i][1] == techos[j][1]:
                    raise ValidationError(
                        _((f"Los niveles de techo no pueden ser iguales"))
                    )
