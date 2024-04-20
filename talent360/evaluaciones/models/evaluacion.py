from odoo import models, fields, http
import base64


class Evaluacion(models.Model):
    _name = "evaluacion"
    _description = "Evaluacion de pesonal"
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
                    print(f"Se ha asignado la evaluación {self.nombre} a {partner_id}")
                    # Send email to assigned user
                    self.message_post(
                        body=f"Se te ha asignado la evaluación {self.nombre}",
                        partner_ids=[partner_id],
                    )
        return res

    def printReport(self):
        # do something
        preguntas_tabuladas = []

        for pregunta in self.pregunta_ids:
            pregunta_tabulada = {"pregunta": pregunta.pregunta_texto, "respuestas": {}}
            for respuesta in pregunta.respuesta_ids:
                if respuesta.respuesta_texto not in pregunta_tabulada["respuestas"]:
                    pregunta_tabulada["respuestas"][respuesta.respuesta_texto] = 0
                pregunta_tabulada["respuestas"][respuesta.respuesta_texto] += 1
            preguntas_tabuladas.append(pregunta_tabulada)

        print(preguntas_tabuladas)

        exportText = str(preguntas_tabuladas)

        # encode the text to bytes, then to base64
        exportText = base64.b64encode(exportText.encode())

        # create an 'ir.attachment' record to hold the download data
        attachment = self.env["ir.attachment"].create(
            {
                "name": "Export.txt",
                "type": "binary",
                "datas": exportText,
                "store_fname": "Export.txt",
            }
        )

        # return an action to download the file
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % (attachment.id),
            "target": "self",
        }

    def reporte_test(self):
        return {
            "type": "ir.actions.act_url",
            "url": "/evaluacion/reporte/%s" % (self.id),
            "target": "self",
        }

   