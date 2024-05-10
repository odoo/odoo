from odoo import models, fields, api
import secrets


class UsuarioEvaluacionRel(models.Model):
    _name = "usuario.evaluacion.rel"
    _description = "Relación entre evaluacion y usuarios"

    evaluacion_id = fields.Many2one("evaluacion", string="Evaluacion")
    usuario_id = fields.Many2one("res.users", string="Usuario")
    contestada = fields.Selection(
        [
            ("pendiente", "Pendiente"),
            ("contestada", "Contestada"),
        ],
        default="pendiente",
    )

    # Campos relacionados para acceder a atributos de evaluacion
    evaluacion_nombre = fields.Char(
        related="evaluacion_id.nombre", string="Nombre de Evaluación", readonly=True
    )
    evaluacion_estado = fields.Selection(
        related="evaluacion_id.estado", string="Estado de Evaluación", readonly=True
    )
    evaluacion_tipo = fields.Selection(
        related="evaluacion_id.tipo", string="Tipo de Evaluación", readonly=True
    )
    evaluacion_usuario_ids = fields.Many2many(
        related="evaluacion_id.usuario_ids",
        string="Usuarios de Evaluación",
        readonly=True,
    )
    token = fields.Char(string="Token")

    def write(self, vals):
        """Sobreescribir el método write para enviar la evaluación al usuario."""
        res = super(UsuarioEvaluacionRel, self).write(vals)
        if "contestada" in vals:
            self.evaluacion_id._compute_porcentaje_respuestas()

        return res

    def action_get_estado(self, usuario_id, evaluacion_id, token):
        """Método para obtener el estado de la evaluación para el usuario.

        :param usuario_id: ID del usuario
        :param evaluacion_id: ID de la evaluación
        :return: estado de la evaluación
        """
        if usuario_id:
            usuario_evaluacion = self.env["usuario.evaluacion.rel"].search(
                [
                    ("usuario_id.id", "=", usuario_id),
                    ("evaluacion_id.id", "=", evaluacion_id),
                ]
            )
        else:
            usuario_evaluacion = self.env["usuario.evaluacion.rel"].search(
                [("evaluacion_id.id", "=", evaluacion_id), ("token", "=", token)]
            )

        return usuario_evaluacion.contestada

    def action_update_estado(self, usuario_id, evaluacion_id, token):
        """Método para actualizar el estado de la evaluación para el usuario.

        :param usuario_id: ID del usuario
        :param evaluacion_id: ID de la evaluación
        """

        if usuario_id:
            usuario_evaluacion = self.env["usuario.evaluacion.rel"].search(
                [
                    ("usuario_id.id", "=", usuario_id),
                    ("evaluacion_id.id", "=", evaluacion_id),
                ]
            )
        else:
            usuario_evaluacion = self.env["usuario.evaluacion.rel"].search(
                [("evaluacion_id.id", "=", evaluacion_id), ("token", "=", token)]
            )

        usuario_evaluacion.write({"contestada": "contestada"})

    def enviar_evaluacion_action(self, evaluacion_id):
        """
        Ejecuta la acción de redireccionar a la lista de evaluaciones y devuelve un diccionario

        Este método utiliza los parámetros necesarios para redireccionar a la lista de evaluaciones

        :return: Un diccionario que contiene todos los parámetros necesarios para redireccionar la
        a una vista de la lista de las evaluaciones.

        """

        length = 32
        base_url = "http://localhost:8069/evaluacion/responder"

        usuario_evaluacion = self.env["usuario.evaluacion.rel"].search(
            [("evaluacion_id.id", "=", evaluacion_id)]
        )

        for user in usuario_evaluacion:
            token = secrets.token_hex(length)
            if not user.token:
                user.write({
                    "token": token,
                    "contestada": "pendiente"
                })

                evaluacion_url = f"{base_url}/{evaluacion_id}/{token}"
                mail_values = {
                    'subject': 'Invitación para completar la evaluación',
                    'email_from': "talent360@cr-organizacional.com",
                    'email_to': user.usuario_id.email,
                    'body_html': 
                        f'''<p>Hola, <strong>{user.usuario_id.name}</strong>,</p>
                        <p>En <strong>{self.env.user.company_id.name}</strong> estamos interesados en tu opinión para mejorar.</p>
                        <p>Por favor, participa en la evaluación de clima laboral disponible del <strong>(Fecha Inicio)</strong> al <strong>(Fecha Fin)</strong>.</p>
                        <p>Puedes comenzar la evaluación haciendo clic en el siguiente enlace:</p>
                        <p><a href="{evaluacion_url}">Comenzar Evaluación</a></p>''',
                }

                mail = self.env['mail.mail'].create(mail_values)
                mail.send()
    
        return {
            "type": "ir.actions.act_window",
            "name": "Evaluaciones",
            "res_model": "evaluacion.evaluacion",
            "view_mode": "tree,form",
            "target": "current",
        }    
    