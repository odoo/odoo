from odoo import api, models, fields
from collections import defaultdict


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

    # Cambiar el titulo del form view
    _rec_name = "nombre"

    # _inherit = ["mail.thread"]

    nombre = fields.Char(required=True)

    tipo = fields.Selection(
        [
            ("CLIMA", "Clima Organizacional"),
            ("NOM_035", "NOM 035"),
            ("competencia", "Competencia"),
        ],
        required=True,
        default="competencia",
    )
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

            new_evaluation = self.env["evaluacion"].create(
                {
                    "nombre": "",
                    "descripcion": "La evaluación Clima es una herramienta de medición de clima organizacional, cuyo objetivo es conocer la percepción que tienen las personas que laboran en los centros de trabajo, sobre aquellos aspectos sociales que conforman su entorno laboral y que facilitan o dificultan su desempeño.",
                    "tipo": "CLIMA",
                }
            )
            self = new_evaluation

        self.pregunta_ids = [(5,)]

        template_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "evaluaciones.template_clima"
        )

        if template_id:
            template = self.env["template"].browse(template_id)
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
            new_evaluation = self.env["evaluacion"].create(
                {
                    "nombre": "",
                    "descripcion": "La NOM 035 tiene como objetivo establecer los elementos para identificar, analizar y prevenir los factores de riesgo psicosocial, así como para promover un entorno organizacional favorable en los centros de trabajo.",
                    "tipo": "NOM_035",
                }
            )
            self = new_evaluation

        self.pregunta_ids = [(5,)]

        template_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "evaluaciones.template_nom035"
        )

        if template_id:
            template = self.env["template"].browse(template_id)
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
            "view_id": self.env.ref("evaluaciones.evaluacion_clima_view_form").id,
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
            "view_id": self.env.ref("evaluaciones.evaluacion_nom035_view_form").id,
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
            "view_id": self.env.ref("evaluaciones.evaluacion_360_view_form").id,
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
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "evaluaciones.evaluacion_competencias_action"
            )
        else:
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "evaluaciones.evaluacion_generica_action"
            )

        action["res_id"] = self.id

        return action

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
            "target": "new",
        }

    def action_generar_datos_reporte_NOM_035(self):
        """
        Genera los datos necesarios para el reporte genérico de la evaluación.

        Esta función genera los parámetros requeridos para generar un reporte genérico de la evaluación actual,
        incluyendo las preguntas y las respuestas tabuladas, agrupadas por categoría y dominio.

        :return: Los parámetros necesarios para generar el reporte.
        """
        parametros = {
            "evaluacion": self,
            "categorias": [],
            "dominios": [],
            "final": 0,
        }

        for pregunta in self.pregunta_ids:
            if not pregunta.categoria:
                continue
            categoria = pregunta.categoria
            dominio = pregunta.dominio

            valor_categoria = 0
            valor_dominio = 0

            for respuesta in pregunta.respuesta_ids:
                valor_respuesta = pregunta.evaluar_respuesta(respuesta.respuesta_texto)
                if pregunta.ponderacion == "ascendente":
                    valor_categoria += valor_respuesta
                    valor_dominio += valor_respuesta
                    parametros["final"] += valor_respuesta
                elif pregunta.ponderacion == "descendente":
                    valor_categoria+= (4 - valor_respuesta)
                    valor_dominio += (4 - valor_respuesta)
                    parametros["final"] += (4 - valor_respuesta)
                    # Verificar si la categoría ya existe en el diccionario de categorías
            for cat in parametros['categorias']:
                if cat['nombre_categoria'] == categoria:
                    cat['valor'] += valor_categoria
                    break
            else:
                datos_categoria = {"nombre_categoria": categoria, "valor": valor_categoria}
                parametros['categorias'].append(datos_categoria)
            
            # Verificar si el dominio ya existe en el diccionario de dominios
            for dom in parametros['dominios']:
                if dom['nombre_dominio'] == dominio:
                    dom['valor'] += valor_dominio
                    break
            else:
                datos_dominio = {"nombre_dominio": dominio, "valor": valor_dominio}
                parametros['dominios'].append(datos_dominio)

        print(parametros)
        return parametros