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
    
    categoria = fields.Selection(
        [
            ("datos_generales", "Datos Generales"),
            ("reclutamiento_y_seleccion_de_personal", "Reclutamiento y Selección de Personal"),
            ("formacion_y_capacitacion", "Formación y Capacitación"),
            ("permanencia_y_ascenso", "Permanencia y Ascenso"),
            ("corresponsabilidad_en_la_vida_laboral_familiar_y_personal", "Corresponsabilidad en la Vida Laboral, Familiar y Personal"),
            ("clima_laboral_libre_de_violencia", "Clima Laboral Libre de Violencia"),
            ("acoso_y_hostigamiento", "Acoso y Hostigamiento"),
            ("accesibilidad", "Accesibilidad"),
            ("respeto_a_la_diversidad", "Respeto a la Diversidad"),
            ("condiciones_generales_de_trabajo", "Condiciones Generales de Trabajo"),
        ],
    )
    
 

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
    
    def evaluar_respuesta(self, respuesta_texto):
        """
        Evalúa el valor de una respuesta en función de la opción seleccionada.

        :param respuesta_texto: El texto de la respuesta seleccionada.
        :return: El valor de la respuesta.
        """
        for opcion in self.opcion_ids:
            if opcion.opcion_texto == respuesta_texto:
                return opcion.valor
        return 0
