from odoo import api, models, fields


class Evaluacion(models.Model):
    """
    Modelo para representar una evaluación de personal en Odoo.

    :param _name (str): Nombre del modelo en Odoo.
    :param _description (str): Descripción del modelo en Odoo.
    :param nombre (fields.Char): Nombre de la evaluación. Es un campo obligatorio.
    :param estado (fields.Selection): Estado de la evaluación con opciones 'borrador', 'publicado' y 'finalizado'. Por defecto, es 'borrador'.
    :param pregunta_ids (fields.Many2many): Relación de muchos a muchos con el modelo 'pregunta' para almacenar las preguntas asociadas a la evaluación.
    :param competencia_ids (fields.Many2many): Relación de muchos a muchos con el modelo 'competencia' para almacenar las competencias asociadas a la evaluación.
    :param usuario_ids (fields.Many2many): Relación de muchos a muchos con el modelo 'res.users' para asignar usuarios a la evaluación.
    """

    _name = "evaluacion"
    _description = "Evaluacion de pesonal"
    # _inherit = ["mail.thread"]

    nombre = fields.Char(required=True)

    tipo = fields.Selection([("CLIMA", "Clima Organizacional"), ("NOM_035", "NOM 035"), ("competencia", "Competencia")],
                            required=True, default="competencia")
    descripcion = fields.Text()
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

    # Método para copiar preguntas de la plantilla a la evaluación
    def copiar_preguntas_de_template(self):
        """
        Copia preguntas de un template de evaluación predeterminado a una nueva evaluación.

        Este método verifica si el objeto actual está vacío (self). Si lo está, crea una nueva
        evaluación con un nombre predeterminado y asigna este nuevo objeto a self. Luego, limpia
        las preguntas existentes y copia todas las preguntas de un template con ID predefinido 
        (en este caso, 332) al objeto evaluación actual.

        Returns:
        object: Retorna el objeto evaluación actualizado con las preguntas copiadas del template.
        """

        if not self:

            new_evaluation = self.env["evaluacion"].create({
                "nombre": "Evaluacion Clima",
                "descripcion": "La valuacion Clima es una herramienta de medición de clima organizacional, cuyo objetivo es conocer la percepción que tienen las personas que laboran en los centros de trabajo, sobre aquellos aspectos sociales que conforman su entorno laboral y que facilitan o dificultan su desempeño.",
                "tipo": "CLIMA",
            })
            self = new_evaluation

        self.pregunta_ids = [(5,)]

        template_id_hardcoded = 1

        if template_id_hardcoded:
            template = self.env["template"].browse(template_id_hardcoded)
            if template:
                pregunta_ids = template.pregunta_ids.ids
                print("IDs de preguntas:", pregunta_ids)
                self.pregunta_ids = [(6, 0, pregunta_ids)]

        return self

    def copiar_preguntas_de_template_nom035(self):
        """
        Copia preguntas de un template de evaluación predeterminado a una nueva evaluación.

        Este método verifica si el objeto actual está vacío (self). Si lo está, crea una nueva
        evaluación con un nombre predeterminado y asigna este nuevo objeto a self. Luego, limpia
        las preguntas existentes y copia todas las preguntas de un template con ID predefinido 
        (en este caso, 331) al objeto evaluación actual.
        
        :return: object: Retorna el objeto evaluación actualizado con las preguntas copiadas del template.
        """

        if not self:
            new_evaluation = self.env["evaluacion"].create({
                "nombre": "NOM 035",
                "descripcion": "La NOM 035 tiene como objetivo establecer los elementos para identificar, analizar y prevenir los factores de riesgo psicosocial, así como para promover un entorno organizacional favorable en los centros de trabajo.",
                "tipo": "NOM_035",
            })
            self = new_evaluation

        self.pregunta_ids = [(5,)]

        template_id_hardcoded = 2

        if template_id_hardcoded:
            template = self.env["template"].browse(template_id_hardcoded)
            if template:
                pregunta_ids = template.pregunta_ids.ids
                self.pregunta_ids = [(6, 0, pregunta_ids)]

        return self

    def evaluacion_clima_action_form(self):
        """
        Ejecuta la acción de copiar preguntas de un template a la evaluación actual y devuelve
        un diccionario con los parámetros necesarios para abrir una ventana de acción en Odoo.

        Este método utiliza `copiar_preguntas_de_template_nom035` para asegurarse de que la evaluación
        actual tenga las preguntas correctas, y luego configura y devuelve un diccionario con
        los detalles para abrir esta evaluación en una vista de formulario específica.

        Returns:
        dict: Un diccionario que contiene todos los parámetros necesarios para abrir la
        evaluación en una vista de formulario específica de Odoo.

        """

        self = self.copiar_preguntas_de_template()

        # Retornar la acción con la vista como destino
        return {
            "type": "ir.actions.act_window",
            "name": "Evaluación Clima",
            "res_model": "evaluacion",
            "view_mode": "form",
            "view_id": self.env.ref("evaluaciones.evaluacion_clima_form").id,
            "target": "current",
            "res_id": self.id,
        }

    def evaluacion_nom035_action_form(self):
        """
        Ejecuta la acción de copiar preguntas de un template a la evaluación actual y devuelve
        un diccionario con los parámetros necesarios para abrir una ventana de acción en Odoo.

        Este método utiliza `copiar_preguntas_de_template_nom035` para asegurarse de que la evaluación
        actual tenga las preguntas correctas, y luego configura y devuelve un diccionario con
        los detalles para abrir esta evaluación en una vista de formulario específica.

        :return: Un diccionario que contiene todos los parámetros necesarios para abrir la
        evaluación en una vista de formulario específica de Odoo.

        """
        self = self.copiar_preguntas_de_template_nom035()

        return {
            "type": "ir.actions.act_window",
            "name": "NOM 035",
            "res_model": "evaluacion",
            "view_mode": "form",
            "view_id": self.env.ref("evaluaciones.evaluacion_nom035_form").id,
            "target": "current",
            "res_id": self.id,
        }

    def evaluacion_360_action_form(self):
        """
        Ejecuta la acción de redireccionar a la evaluación 360 y devuelve un diccionario

        Este método utiliza los parámetros necesarios para redireccionar a la evaluación 360

        :return: Un diccionario que contiene todos los parámetros necesarios para redireccionar la
        a una vista de la evaluación 360.

        """
        self.tipo = "competencia"
        return {
            "type": "ir.actions.act_window",
            "name": "360",
            "res_model": "evaluacion",
            "view_mode": "form",
            "view_id": self.env.ref("evaluaciones.evaluacion_360_form").id,
            "target": "current",
            "res_id": self.id,
        }

    def evaluacion_action_tree(self):
        """
        Ejecuta la acción de redireccionar a la lista de evaluaciones y devuelve un diccionario

        Este método utiliza los parámetros necesarios para redireccionar a la lista de evaluaciones

        :return: Un diccionario que contiene todos los parámetros necesarios para redireccionar la
        a una vista de la lista de las evaluaciones.

        """

        return {
            "name": "Evaluación",
            "type": "ir.actions.act_window",
            "res_model": "evaluacion",
            "view_mode": "tree",
            "target": "current",
        }

    def abrir_evaluacion_form(self):
        """
        Abre la evaluación en una vista de formulario.

        Este método configura y devuelve un diccionario con los detalles para abrir la evaluación
        actual en una vista de formulario específica dependiendo de su tipo.

        :return: Un diccionario que contiene todos los parámetros necesarios para abrir la
        evaluación en una vista de formulario específica de Odoo.

        """

        if self.tipo == "competencia":
            view_id = self.env.ref("evaluaciones.evaluacion_360_form").id
        else:
            view_id = self.env.ref("evaluaciones.evaluacion_reporte_form").id

        return {
            "type": "ir.actions.act_window",
            "name": "Evaluación",
            "res_model": "evaluacion",
            "view_mode": "form",
            "view_id": view_id,
            "target": "current",
            "res_id": self.id,
        }

    def action_reporte_generico(self):
        """
        Genera una acción de URL para el reporte genérico de la evaluación.

        Esta función genera un URL para redirigir
        a un reporte específico de la evaluación actual.

        :return: una acción de redirección al reporte de la evaluación

        """
        return {
            "type": "ir.actions.act_url",
            "url": "/evaluacion/reporte/%s" % (self.id),
            "target": "self",
    } 


    def action_generar_datos_reporte_generico(self):

        """
        Genera los datos necesarios para el reporte genérico de la evaluación.

        Esta función genera los parámetros requeridos para generar un reporte genérico de la evaluación actual,
        incluyendo las preguntas y las respuestas tabuladas.

        :return: Los parámetros necesarios para generar el reporte.

        """
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
