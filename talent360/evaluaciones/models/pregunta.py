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
    :param preguntas_desbloqueadas (fields.Many2many): Relación muchos a muchos con el modelo 'pregunta' para las preguntas desbloqueadas por la respuesta trigger.
    :param categoria (fields.Selection): Categoría de la pregunta con opciones 'ambiente_de_trabajo', 'factores_actividad', 'organizacion_tiempo', 'liderazgo_relaciones', 'datos_generales', 'reclutamiento_y_seleccion_de_personal', 'formacion_y_capacitacion', 'permanencia_y_ascenso', 'corresponsabilidad_en_la_vida_laboral_familiar_y_personal', 'clima_laboral_libre_de_violencia', 'acoso_y_hostigamiento', 'accesibilidad', 'respeto_a_la_diversidad' y 'condiciones_generales_de_trabajo'.
    :param dominio (fields.Selection): Dominio de la pregunta con opciones 'condiciones_ambiente', 'carga_trabajo', 'falta_control', 'jornada_trabajo', 'trabajo_familia', 'liderazgo', 'relaciones' y 'violencia'.
    :param valor_maximo (fields.Float): Valor máximo de la pregunta. Calculado en función del tipo de pregunta.
    """

    _name = "pregunta"
    _description = "Pregunta para una evaluación"
    _rec_name = "pregunta_texto"

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
    respuesta_ids = fields.One2many(
        "respuesta", "pregunta_id", string="Respuestas")
    competencia_ids = fields.Many2many("competencia", string="Competencias")
    condicional = fields.Boolean(default=False)
    respuesta_trigger = fields.Many2one("opcion", string="Respuesta trigger")
    preguntas_desbloqueadas = fields.Many2many(
        "pregunta",
        "pregunta_rel",
        "pregunta_id",
        "desbloqueada_id",
        string="Preguntas desbloqueadas",
    )

    categoria = fields.Selection(
        [
            ("ambiente_de_trabajo", "Ambiente de Trabajo"),
            ("factores_actividad", "Factores propios de la actividad"),
            ("organizacion_tiempo", "Organización del tiempo de trabajo"),
            ("liderazgo_relaciones", "Liderazgo y relaciones en el trabajo"),
            ("datos_generales", "Datos Generales"),
            (
                "reclutamiento_y_seleccion_de_personal",
                "Reclutamiento y Selección de Personal",
            ),
            ("formacion_y_capacitacion", "Formación y Capacitación"),
            ("permanencia_y_ascenso", "Permanencia y Ascenso"),
            (
                "corresponsabilidad_en_la_vida_laboral_familiar_y_personal",
                "Corresponsabilidad en la Vida Laboral, Familiar y Personal",
            ),
            ("clima_laboral_libre_de_violencia",
             "Clima Laboral Libre de Violencia"),
            ("acoso_y_hostigamiento", "Acoso y Hostigamiento"),
            ("accesibilidad", "Accesibilidad"),
            ("respeto_a_la_diversidad", "Respeto a la Diversidad"),
            ("condiciones_generales_de_trabajo",
             "Condiciones Generales de Trabajo"),
        ],
    )

    dominio = fields.Selection(
        [
            ("condiciones_ambiente", "Condiciones en el ambiente de trabajo"),
            ("carga_trabajo", "Carga de trabajo"),
            ("falta_control", "Falta de control sobre el trabajo"),
            ("jornada_trabajo", "Jornada de trabajo"),
            ("trabajo_familia", "Interferencia en la relación trabajo-familia"),
            ("liderazgo", "Liderazgo"),
            ("relaciones", "Relaciones en el trabajo"),
            ("violencia", "Violencia"),
        ],
    )

    def _calculate_valor_maximo(self):
        if self.tipo == "escala":
            return 4
        elif self.tipo == "multiple_choice":
            return max(self.opcion_ids.mapped("valor"))
        else:
            return 0

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
            return self.preguntas_desbloqueadas
        return False
