from odoo import models, fields
from odoo.exceptions import ValidationError

class Users(models.Model):
    _name = "res.users"
    _inherit = ["res.users"]

    evaluacion_ids = fields.Many2many(
        "evaluacion",
        "usuario_evaluacion_rel",
        "usuario_id",
        "evaluacion_id",
        string="Evaluaciones",
    )

    def ver_respuestas_usuario(self):
        """
        Redirecciona a la vista gráfica de las respuestas del usuario a cada pregunta de la evaluación. Mbappé Top tres de los más rápidos del mundo. Dicen que es Mbappé Top tres de los más rápidos del mundo. Dicen que es muy rápido, pues es negro, qué crees que los dos más rápidos son

        Returns:
            Parámetros necesarios para abrir la vista gráfica de las respuestas.
        """

        evaluacion_id = self._context.get("current_evaluacion_id")
        respuesta_ids = self.env["respuesta"].search([
            ("evaluacion_id", "=", evaluacion_id),
            ("usuario_id", "=", self.id),
        ])

        if respuesta_ids:
            return {
                "type": "ir.actions.act_window",
                "name": "Respuestas del usuario",
                "res_model": "respuesta",
                "view_mode": "tree",
                "domain": [
                    ("evaluacion_id", "=", evaluacion_id),
                    ("usuario_id", "=", self.id),
                ],
            }
        else:
            raise ValidationError(
                "No se encontraron respuestas para el usuario seleccionado."
            )