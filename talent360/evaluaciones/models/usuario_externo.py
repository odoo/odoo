from odoo import models, fields
from odoo.exceptions import ValidationError


class UsuarioExterno(models.Model):

    _name = "usuario.externo"
    _description = "Usuarios externos a la plataforma. Se utiliza para que puedan responer encuestas sin tener un usuario"
    _rec_name = "nombre"

    nombre = fields.Char(string="Nombre Completo", required=True)
    email = fields.Char(string="Correo electrónico", required=True)
    puesto = fields.Char()
    nivel_jerarquico = fields.Char(string="Nivel jerárquico")
    direccion = fields.Char(string="Dirección")
    gerencia = fields.Char(string="Gerencia")
    jefatura = fields.Char(string="Jefatura")
    genero = fields.Char(string="Género")
    fecha_ingreso = fields.Date(string="Fecha de ingreso")
    fecha_nacimiento = fields.Date(string="Fecha de nacimiento")
    region = fields.Char(string="Ubicación/Región")

    evaluacion_ids = fields.Many2many(
        "evaluacion",
        "usuario_evaluacion_rel",
        "usuario_externo_id",
        "evaluacion_id",
        string="Evaluaciones",
    )

    def ver_respuestas_usuario_externo(self):
        evaluacion_id = self._context.get("current_evaluacion_id")

        usuario_evaluacion_rel = self.env["usuario.evaluacion.rel"].search(
            [("evaluacion_id.id", "=", evaluacion_id), ("usuario_externo_id.id", "=", self.id)]
        )

        if not usuario_evaluacion_rel:
            raise ValidationError(
                "No se encontraron respuestas para el usuario seleccionado. test"
            )

        if len(usuario_evaluacion_rel) > 1:
            raise ValidationError(
                "El usuario seleccionado está asognado a la evaluación multiples veces. Por favor contactar a un administrador."
            )
            
        token = usuario_evaluacion_rel.token

        respuesta_ids = self.env["respuesta"].search(
            [
                ("evaluacion_id.id", "=", evaluacion_id),
                ("token", "=", token),
            ]
        )

        if respuesta_ids:
            return {
                "type": "ir.actions.act_window",
                "name": "Respuestas del usuario",
                "res_model": "respuesta",
                "view_mode": "tree",
                "domain": [
                    ("evaluacion_id", "=", evaluacion_id),
                    ("token", "=", token),
                ],
            }
        else:
            raise ValidationError(
                "No se encontraron respuestas para el usuario seleccionado."
            )
