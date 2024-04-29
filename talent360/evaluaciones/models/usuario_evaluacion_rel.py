from odoo import models, fields, api
import secrets

class UsuarioEvaluacionRel(models.Model):
    _name = "usuario.evaluacion.rel"
    _description = "Relación entre evaluacion y usuarios"

    evaluacion_id = fields.Many2one("evaluacion", string="Evaluacion")
    usuario_id = fields.Many2one("res.users", string="Usuario")
    contestada = fields.Boolean("contestada", default=False)
    token = fields.Char(string="Token")
    
    def action_get_estado(self, user_id, evaluacion_id):
        """Método para obtener el estado de la evaluación para el usuario.
        
        :param user_id: ID del usuario
        :param evaluacion_id: ID de la evaluación
        :return: estado de la evaluación
        """
        usuario_evaluacion = self.env["usuario.evaluacion.rel"].search(
            [("usuario_id", "=", user_id), ("evaluacion_id", "=", evaluacion_id)]
        )
        return usuario_evaluacion.contestada

    def action_update_estado(self, user_id, evaluacion_id):
        """Método para actualizar el estado de la evaluación para el usuario.
        
        :param user_id: ID del usuario
        :param evaluacion_id: ID de la evaluación
        """
        usuario_evaluacion = self.env["usuario.evaluacion.rel"].search(
            [("usuario_id", "=", user_id), ("evaluacion_id", "=", evaluacion_id)]
        )

    def action_enviar_evaluacion(self, evaluacion_id):
        """
        Ejecuta la acción de redireccionar a la lista de evaluaciones y devuelve un diccionario

        Este método utiliza los parámetros necesarios para redireccionar a la lista de evaluaciones

        :return: Un diccionario que contiene todos los parámetros necesarios para redireccionar la
        a una vista de la lista de las evaluaciones.

        """

        length = 32

        usuario_evaluacion = self.env["usuario.evaluacion.rel"].search(
            [("evaluacion_id", "=", evaluacion_id)]
        )

        for user in usuario_evaluacion:
            token = secrets.token_hex(length)
            user.write({"token": token})