from odoo import models, fields


class Evaluacion(models.Model):
    _name = "evaluacion"
    _description = "Evaluacion de personal"
    _inherit = ["mail.thread"]

    nombre = fields.Char(required=True)
    estado = fields.Selection(
        [
            ("borrador", "Borrador"),
            ("publicado", "Publicado"),
            ("finalizado", "Finalizado"),
        ],
        default="borrador",
        required=True,
    )

    pregunta_ids = fields.Many2many(
        "pregunta",
        "pregunta_evaluacion_rel",
        "evaluacion_id",
        "pregunta_id",
        string="Preguntas",
    )

    competencia_ids = fields.Many2many(
        "competencia",
        "competencia_evaluacion_rel",
        "evaluacion_id",
        "competencia_id",
        string="Competencias",
    )

    usuario_ids = fields.Many2many(
        "res.users",
        "usuario_evaluacion_rel",
        "evaluacion_id",
        "usuario_id",
        string="Asignados",
    )

    # do something on new usuario assigned

    def write(self, vals):
        res = super(Evaluacion, self).write(vals)
        if "usuario_ids" in vals:
            for user_change in vals["usuario_ids"]:
                action, user_id = user_change
                user = self.env["res.users"].browse(user_id)
                partner_id = user.partner_id.id
                if action == 4:
                    # Send email to assigned user
                    self.message_post(
                        body=f"Se te ha asignado la evaluación {self.nombre}",
                        partner_ids=[partner_id],
                    )
        return res

    def action_reporte_generico(self):
        return {
            "type": "ir.actions.act_url",
            "url": "/evaluacion/reporte/%s" % (self.id),
            "target": "self",
        }

    def action_generar_datos_reporte_generico(self):
        parametros = {
            "evaluacion": self,
            "preguntas": [],
        }

        respuesta_tabulada = {}

        for pregunta in self.pregunta_ids:

            respuestas = []
            respuestas_tabuladas = []

            for respuesta in pregunta.respuesta_ids:
                respuestas.append(respuesta.respuesta_texto)

                for i, respuesta_tabulada in enumerate(respuestas_tabuladas):
                    if respuesta_tabulada["texto"] == respuesta.respuesta_texto:
                        respuestas_tabuladas[i]["conteo"] += 1
                        break
                else:
                    respuestas_tabuladas.append(
                        {"texto": respuesta.respuesta_texto, "conteo": 1}
                    )

            datos_pregunta = {
                "pregunta": pregunta,
                "respuestas": respuestas,
                "respuestas_tabuladas": respuestas_tabuladas,
                "datos_grafica": str(respuestas_tabuladas).replace("'", '"'),
            }

            parametros["preguntas"].append(datos_pregunta)

        return parametros
