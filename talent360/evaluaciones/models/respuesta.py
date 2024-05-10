from odoo import models, fields


class Respuesta(models.Model):
    """
    Modelo para representar las respuestas a las preguntas
    
    :param _name (str): Nombre del modelo en Odoo
    :param _description (str): Descripción del modelo en Odoo
    :param pregunta_id (int): Identificador de la pregunta
    :param usuario_id (int): Identificador del usuario
    :param evaluacion_id (int): Identificador de la evaluación
    :param pregunta_texto (str): Texto de la pregunta
    :param respuesta_texto (str): Texto de la respuesta
    :param token (str): Token de la respuesta
    :param opcion_id (int): Identificador de la opción
    :param respuesta_mostrar (str): Respuesta a mostrar
    """
    
    _name = "respuesta"
    _description = "Respuesta a una pregunta"
    _rec_name = "respuesta_mostrar"

    pregunta_id = fields.Many2one("pregunta", string="Preguntas")
    usuario_id = fields.Many2one("res.users", string="Usuario")
    evaluacion_id = fields.Many2one("evaluacion", string="Evaluacion")
    pregunta_texto = fields.Char(related="pregunta_id.pregunta_texto")
    respuesta_texto = fields.Char("Respuesta")
    token = fields.Char()
    opcion_id = fields.Many2one("opcion", string="Opción")

    respuesta_mostrar = fields.Char(
        string="Respuesta", compute="_compute_respuesta_mostrar"
    )

    valor_respuesta = fields.Float(
        string="Valor de la respuesta",
        compute="_compute_valor_respuesta",
        store=False,
    )

    def guardar_respuesta_action(
        self, radios, texto, evaluacion_id, usuario_id, pregunta_id, token, scale=False
    ):
        """Método para guardar la respuesta de una pregunta.
        Este método se encarga de guardar la respuesta de una pregunta en la base de datos.
        """

        resp = None

        if usuario_id:
            if scale:
                resp = self.env["respuesta"].create(
                    {
                        "evaluacion_id": evaluacion_id,
                        "usuario_id": usuario_id,
                        "pregunta_id": pregunta_id,
                        "respuesta_texto": radios,
                    }
                )

            elif texto:
                resp = self.env["respuesta"].create(
                    {
                        "evaluacion_id": evaluacion_id,
                        "usuario_id": usuario_id,
                        "pregunta_id": pregunta_id,
                        "respuesta_texto": texto,
                    }
                )

            elif radios:
                resp = self.env["respuesta"].create(
                    {
                        "evaluacion_id": evaluacion_id,
                        "usuario_id": usuario_id,
                        "pregunta_id": pregunta_id,
                        "opcion_id": radios,
                    }
                )

        else:
            if scale:
                resp = self.env["respuesta"].create(
                    {
                        "evaluacion_id": evaluacion_id,
                        "token": token,
                        "pregunta_id": pregunta_id,
                        "respuesta_texto": radios,
                    }
                )

            elif texto:
                resp = self.env["respuesta"].create(
                    {
                        "evaluacion_id": evaluacion_id,
                        "token": token,
                        "pregunta_id": pregunta_id,
                        "respuesta_texto": texto,
                    }
                )

            elif radios:
                resp = self.env["respuesta"].create(
                    {
                        "evaluacion_id": evaluacion_id,
                        "token": token,
                        "pregunta_id": pregunta_id,
                        "opcion_id": radios,
                    }
                )

        return resp

    def _compute_respuesta_mostrar(self):
        for record in self:
            respuesta_texto = "N/A"

            if record.pregunta_id.tipo == "escala":
                respuesta_texto = record.pregunta_id.mapeo_valores_escala[record.pregunta_id.ponderacion][record.respuesta_texto]
            elif record.pregunta_id.tipo == "multiple_choice":
                respuesta_texto = record.opcion_id.opcion_texto
            else:
                respuesta_texto = record.respuesta_texto

            record.respuesta_mostrar = respuesta_texto

    def _compute_valor_respuesta(self):
        for record in self:
            if record.pregunta_id.tipo == "escala":
                record.valor_respuesta = int(record.respuesta_texto)
            elif record.pregunta_id.tipo == "multiple_choice":
                record.valor_respuesta = record.opcion_id.valor
            else:
                record.valor_respuesta = 0