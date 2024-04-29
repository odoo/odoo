from odoo import models, fields


class Respuesta(models.Model):
    _name = "respuesta"
    _description = "Respuesta a una pregunta"

    pregunta_id = fields.Many2one("pregunta", string="Preguntas")
    user_id = fields.Many2one("res.users", string="Usuario")
    evaluacion_id = fields.Many2one("evaluacion", string="Evaluacion")

    respuesta_texto = fields.Char("Respuesta", required=True)


    def action_guardar_respuesta(self, radios, texto, evaluacion_id, user_id, pregunta_id):
        """Método para guardar la respuesta de una pregunta.
        Este método se encarga de guardar la respuesta de una pregunta en la base de datos.
        """

        resp = None

        if texto:
            resp = self.env["respuesta"].create({
                "evaluacion_id": evaluacion_id,
                "user_id": user_id,
                "pregunta_id": pregunta_id,
                "respuesta_texto": texto
            })

        if radios:
            resp = self.env["respuesta"].create({
                "evaluacion_id": evaluacion_id,
                "user_id": user_id,
                "pregunta_id": pregunta_id,
                "respuesta_texto": radios
            })
            
        return resp
