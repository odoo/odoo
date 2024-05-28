from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Niveles(models.Model):

    _name = "niveles"
    _description = "Niveles de semaforización"

    evaluacion_id = fields.Many2one("evaluacion", string="Evaluación")
    descripcion_nivel = fields.Char(string="Descripción", default="Muy malo")
    techo = fields.Integer(string="Ponderación", default=0)
    color = fields.Char(string="Color", default="red")

    @api.constrains("techo", "evaluacion_id")
    def _check_techo(self):
        for record in self:
            # Verificar que el valor de la ponderación sea mayor que 0
            if record.techo <= 0:
                raise ValidationError(
                    "El valor de la ponderación debe ser mayor que 0."
                )

            # Verificar que no haya valores duplicados en la ponderación para la misma evaluación
            niveles = self.search(
                [
                    ("evaluacion_id", "=", record.evaluacion_id.id),
                    ("id", "!=", record.id),
                ]
            )
            techos = niveles.mapped("techo")
            if record.techo in techos:
                raise ValidationError(
                    "No puede haber valores duplicados en la ponderación."
                )

            # Verificar que los valores de la ponderación estén en orden ascendente
            todos_niveles = self.search(
                [("evaluacion_id", "=", record.evaluacion_id.id)]
            )
            todos_techos = todos_niveles.mapped("techo")
            if todos_techos != sorted(todos_techos):
                raise ValidationError(
                    "Los valores de la ponderación deben estar en orden ascendente."
                )

            # Verificar que no haya más de 10 techos
            if len(todos_techos) > 10:
                raise ValidationError(
                    "No puede haber más de 10 valores de ponderación."
                )

            # Verificar que el valor de los 'techos' no sean mayores a 100 y que el último sea 100
            if record.techo > 100:
                raise ValidationError(
                    "El valor de la ponderación no puede ser mayor a 100."
                )
            if todos_techos[-1] != 100:
                raise ValidationError("El último valor de la ponderación debe ser 100.")
