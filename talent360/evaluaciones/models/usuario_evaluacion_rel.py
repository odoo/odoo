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
    evaluacion_nombre = fields.Char(related="evaluacion_id.nombre", string="Nombre de Evaluación", readonly=True)
    evaluacion_estado = fields.Selection(related="evaluacion_id.estado", string="Estado de Evaluación", readonly=True)
    evaluacion_tipo = fields.Selection(related="evaluacion_id.tipo", string="Tipo de Evaluación", readonly=True)
    evaluacion_usuario_ids = fields.Many2many(related="evaluacion_id.usuario_ids", string="Usuarios de Evaluación", readonly=True)
    token = fields.Char(string="Token")
    
    
    def action_get_estado(self, user_id, evaluacion_id, token):
        """Método para obtener el estado de la evaluación para el usuario.
        
        :param user_id: ID del usuario
        :param evaluacion_id: ID de la evaluación
        :return: estado de la evaluación
        """
        if user_id:
            usuario_evaluacion = self.env["usuario.evaluacion.rel"].search(
                [("usuario_id", "=", user_id), ("evaluacion_id", "=", evaluacion_id)]
            )
        else:
            usuario_evaluacion = self.env["usuario.evaluacion.rel"].search(
                [("evaluacion_id", "=", evaluacion_id), ("token", "=", token)]
            )

        return usuario_evaluacion.contestada

    def action_update_estado(self, user_id, evaluacion_id, token):
        """Método para actualizar el estado de la evaluación para el usuario.
        
        :param user_id: ID del usuario
        :param evaluacion_id: ID de la evaluación
        """
        
        if user_id:
            usuario_evaluacion = self.env["usuario.evaluacion.rel"].search(
                [("usuario_id", "=", user_id), ("evaluacion_id", "=", evaluacion_id)]
            )
        else:
            usuario_evaluacion = self.env["usuario.evaluacion.rel"].search(
                [("evaluacion_id", "=", evaluacion_id), ("token", "=", token)]
            )

        usuario_evaluacion.write({"contestada": "contestada"})

    def action_enviar_evaluacion(self, evaluacion_id):
        """
        Ejecuta la acción de redireccionar a la lista de evaluaciones y devuelve un diccionario

        Este método utiliza los parámetros necesarios para redireccionar a la lista de evaluaciones

        :return: Un diccionario que contiene todos los parámetros necesarios para redireccionar la
        a una vista de la lista de las evaluaciones.

        """

        length = 32
        base_url = "http://localhost:8069/evaluacion/responder"

        usuario_evaluacion = self.env["usuario.evaluacion.rel"].search(
            [("evaluacion_id", "=", evaluacion_id)]
        )

        for user in usuario_evaluacion:
            token = secrets.token_hex(length)
            if not user.token:
                user.write({
                    "token": token,
                    "contestada": "pendiente"
                })

                print(f'{base_url}/{evaluacion_id}/{token}')
                mail_values = {
                    'subject': 'Invitación para completar la evaluación',
                    'email_from': self.env.user.email_formatted,
                    'email_to': user.usuario_id.email,
                    'body_html': f'<p>Hola, <strong>{user.usuario_id.name}</strong></p>'
                                f'<p>En <strong>{self.env.user.company_id.name}</strong> estamos muy interesados'
                                f'<p>en conocer tu opinión, a fin de identificar áreas de mejora que nos permitan mejorar</p>'
                                f'<p>tu experiencia con nosotros. Por ello, te invitamos a responder la Encuesta de Clima</p>'
                                f'<p>Laboral: <strong>(Nombre de evaluación)</strong></p>'
                                f'<p>Disponible del <strong>(Fecha Inicio)</strong> al <strong>(Fecha Fin)</strong></p>'
                                f'<a href="{base_url}/{evaluacion_id}/{token}">',
                }

                mail = self.env['mail.mail'].create(mail_values)
                # mail.send()

                if mail.state == 'sent':
                    print(f"Correo enviado exitosamente a {user.usuario_id.email}")
                elif mail.state == 'exception':
                    print(f"Fallo al enviar correo a {user.usuario_id.email}")
                else:
                    print(f"Correo en estado pendiente o desconocido: {mail.state}")
    
        # return {
        #     "type": "ir.actions.act_window",
        #     "name": "Evaluaciones",
        #     "res_model": "evaluacion",
        #     "view_mode": "tree",
        #     "target": "current",
        # }        
    
