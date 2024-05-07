from odoo import models, fields


class Respuesta(models.Model):
    _name = "respuesta"
    _description = "Respuesta a una pregunta"

    pregunta_id = fields.Many2one("pregunta", string="Preguntas")
    usuario_id = fields.Many2one("res.users", string="Usuario")
    evaluacion_id = fields.Many2one("evaluacion", string="Evaluacion")
    pregunta_texto = fields.Char(related="pregunta_id.pregunta_texto")

    respuesta_texto = fields.Char("Respuesta")

    token = fields.Char(string="Token")

    opcion_id = fields.Many2one("opcion", string="Opción")

    def action_guardar_respuesta(self, radios, texto, evaluacion_id, user_id, pregunta_id, token, scale=False):
        """Método para guardar la respuesta de una pregunta.
        Este método se encarga de guardar la respuesta de una pregunta en la base de datos.
        """

        resp = None

        if user_id:
            if scale:
                resp = self.env["respuesta"].create({
                    "evaluacion_id": evaluacion_id,
                    "user_id": user_id,
                    "pregunta_id": pregunta_id,
                    "respuesta_texto": radios
                })

            elif texto:
                resp = self.env["respuesta"].create({
                    "evaluacion_id": evaluacion_id,
                    "user_id": user_id,
                    "pregunta_id": pregunta_id,
                    "respuesta_texto": texto
                })

            elif radios:
                resp = self.env["respuesta"].create({
                    "evaluacion_id": evaluacion_id,
                    "user_id": user_id,
                    "pregunta_id": pregunta_id,
                    "opcion_id": radios
                })

        else:
            if scale:
                resp = self.env["respuesta"].create({
                    "evaluacion_id": evaluacion_id,
                    "token": token,
                    "pregunta_id": pregunta_id,
                    "respuesta_texto": radios
                })

            elif texto:
                resp = self.env["respuesta"].create({
                    "evaluacion_id": evaluacion_id,
                    "token": token,
                    "pregunta_id": pregunta_id,
                    "respuesta_texto": texto
                })

            elif radios:
                resp = self.env["respuesta"].create({
                    "evaluacion_id": evaluacion_id,
                    "token": token,
                    "pregunta_id": pregunta_id,
                    "opcion_id": radios
                })
            
        return resp
