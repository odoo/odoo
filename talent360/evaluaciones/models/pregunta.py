from odoo import models, fields


class Pregunta(models.Model):
    """
    Modelo para representar una pregunta de una evaluación en Odoo.

    :param _name (str): Nombre del modelo en Odoo.
    :param _description (str): Descripción del modelo en Odoo.
    :param pregunta_texto (fields.Char): Texto de la pregunta. Es un campo obligatorio.
    :param tipo (fields.Selection): Tipo de pregunta con opciones 'multiple_choice', 'open_question' y 'escala'. Por defecto, es 'multiple_choice'.
    :param opcion_ids (fields.One2many): Relación uno a muchos con el modelo 'opcion' para las opciones de respuesta asociadas a la pregunta.
    :param respuesta_ids (fields.One2many): Relación uno a muchos con el modelo 'respuesta' para las respuestas asociadas a la pregunta.
    :param competencia_ids (fields.Many2many): Relación muchos a muchos con el modelo 'competencia' para las competencias asociadas a la pregunta.
    :param condicional (fields.Boolean): Indica si la pregunta es condicional. Por defecto, es False.
    :param respuesta_trigger (fields.Many2one): Relación muchos a uno con el modelo 'opcion' para la respuesta que desbloquea la pregunta.
    :param preguntas_desbloquadas (fields.Many2many): Relación muchos a muchos con el modelo 'pregunta' para las preguntas desbloqueadas por la respuesta trigger.
    """

    _name = "pregunta"
    _description = "Pregunta para una evaluación"

    pregunta_texto = fields.Char("Pregunta", required=True)
    tipo = fields.Selection(
        [
            ("multiple_choice", "Opción múltiple"),
            ("open_question", "Abierta"),
            ("escala", "Escala"),
        ],
        default="multiple_choice",
        required=True,
    )

    opcion_ids = fields.One2many("opcion", "pregunta_id", string="Opciones")
    respuesta_ids = fields.One2many("respuesta", "pregunta_id", string="Respuestas")
    competencia_ids = fields.Many2many("competencia", string="Competencias")
    condicional = fields.Boolean("Condicional", default=False)
    respuesta_trigger = fields.Many2one("opcion", string="Respuesta trigger")
    preguntas_desbloqueadas = fields.Many2many(
        "pregunta", 
        "pregunta_rel", 
        "pregunta_id", 
        "desbloqueada_id", 
        string="Preguntas desbloqueadas")

    def ver_respuestas(self):
        """
        Redirecciona a la vista gráfica de las respuestas filtradas por evaluación y pregunta.

        Returns:
            Parámetros necesarios para abrir la vista gráfica de las respuestas.
        """
        evaluacion_id = self._context.get("current_evaluacion_id")
        # Redirect to graph view of respuestas filtered by evaluacion_id and pregunta_id grouped by respuesta
        return {
            "type": "ir.actions.act_window",
            "name": "Respuestas",
            "res_model": "respuesta",
            "view_mode": "graph",
            "domain": [
                ("evaluacion_id", "=", evaluacion_id),
                ("pregunta_id", "=", self.id),
            ],
            "context": {"group_by": "respuesta_texto"},
        }
    
    def handle_condition(self, respuesta):
        """
        Maneja la condición de la pregunta.

        Args:
            respuesta (opcion): Opción seleccionada por el usuario.

        Returns:
            Preguntas desbloqueadas por la respuesta trigger.
        """
        if self.condicional and respuesta == self.respuesta_trigger:
            print(self.preguntas_desbloquadas)
            return self.preguntas_desbloquadas
        return False
