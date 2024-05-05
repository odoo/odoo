from odoo import models, fields


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

        evaluacion_id = self._context.get("current_evaluacion_id")

        return {
            "type": "ir.actions.act_window",
            "name": "respuesta_usuario",
            "res_model": "respuesta",
            "view_mode": "tree",
            "domain": [
                ("evaluacion_id", "=", evaluacion_id),
                ("usuario_id", "=", self.id),
                ],
            "context": {"group_by": "respuesta_texto"},
        }
