from odoo import models, fields, api

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
        usuario_evaluacion.contestada = True

    def create(self, vals):
        from ..controllers.token_generator import TokenGenerator
        vals["token"] = TokenGenerator.generate_token()
        return super(UsuarioEvaluacionRel, self).create(vals)

    
    def write(self, vals):
        from ..controllers.token_generator import TokenGenerator
        if "usuario_id" in vals or "evaluacion_id" in vals:
            vals["token"] = TokenGenerator.generate_token()
        return super(UsuarioEvaluacionRel, self).write(vals)