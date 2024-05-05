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

        # Obtener el modelo de la relación entre evaluacion y usuarios
        usuario_evaluacion_rel_model = self.env["usuario.evaluacion.rel"]
    
        # Crear o actualizar un registro en la relación
        usuario_evaluacion_rel = usuario_evaluacion_rel_model.create({
            "evaluacion_id": evaluacion_id,
            "contestada": "Contestada"  # Establecer el valor para el campo "Contestada" como una de las opciones disponibles
        })

        return {
            "type": "ir.actions.act_window",
            "name": "Respuesta usuario",
            "res_model": "repuesta",
            "view_mode": "kanban",
            "domain": [
                ("evaluacion_id", "=", evaluacion_id),
                ],
            "context": {"group_by": "respuesta_texto"},
        }
