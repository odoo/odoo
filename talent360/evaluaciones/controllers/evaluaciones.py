from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError
from ..models.evaluacion import Evaluacion
from ..models.respuesta import Respuesta as respuesta
from ..models.pregunta import Pregunta as pregunta
import json


class EvaluacionesController(http.Controller):
    """Controlador para manejar las solicitudes relacionadas con las evaluaciones."""

    @http.route(
        "/evaluacion/reporte/<model('evaluacion'):evaluacion>", type="http", auth="user"
    )
    def reporte_controler(self, evaluacion: Evaluacion):
        """Método para generar y mostrar un reporte de evaluación.
        Este método verifica que el usuario tenga los permisos necesario, obtiene los datos
        del modelo de evaluaciones y renderiza el reporte con esos datos.

        :return: html renderizado del template con los datos del reporte
        """

        if not request.env.user.has_group(
            "evaluaciones.evaluaciones_cliente_cr_group_user"
        ):
            raise AccessError("No tienes permitido acceder a este recurso.")

        parametros = evaluacion.action_generar_datos_reporte_generico()

        return request.render("evaluaciones.encuestas_reporte", parametros)
    
    @http.route(
        "/evaluacion/responder/<model('evaluacion'):evaluacion>", type="http", auth="user", website=True
    )
    def responder_evaluacion_controller(self, evaluacion: Evaluacion):
        """Método para desplegar el formulario de permitir al usuario responder una evaluación.
        Este método verifica que el usuario tenga los permisos necesario, obtiene los datos
        del modelo de evaluaciones y renderiza el formulario con esos datos.

        :return: html renderizado del template con los datos del formulario
        """

        if not request.env.user.has_group(
            "evaluaciones.evaluaciones_cliente_cr_group_user"
        ):
            raise AccessError("No tienes permitido acceder a este recurso.")
        
        evaluacion_id = evaluacion.id

        # Obtén la evaluación basada en el ID
        parametros = evaluacion.action_get_evaluaciones(evaluacion_id)
        
        # Renderiza la plantilla con la evaluación
        return request.render('evaluaciones.evaluaciones_responder', parametros)
    
    @http.route(
        "/evaluacion/responder", type="http", auth="user", website=True, methods=["POST"], csrf=False
    )
    def responder_evaluacion_controller_post(self, **post):
        """Método para procesar la respuesta del formulario de evaluación.
        Este método verifica que el usuario tenga los permisos necesario, obtiene los datos
        del modelo de evaluaciones y guarda la respuesta del usuario.

        :return: redirección a la página de inicio
        """

        if not request.env.user.has_group(
            "evaluaciones.evaluaciones_cliente_cr_group_user"
        ):
            raise AccessError("No tienes permitido acceder a este recurso.")
        
        post_data = json.loads(request.httprequest.data)

        radio_values = post_data.get('radioValues')
        textarea_values = post_data.get('textareaValues')
        evaluacion_id = post_data.get('evaluacion_id')
        user_id = request.env.user.id
        respuesta_model = request.env['respuesta']

        for pregunta_id, radio_value in radio_values.items():
            if pregunta_id in radio_values:
                radio_value = radio_values[pregunta_id]
                resp = respuesta_model.sudo().action_guardar_respuesta(radio_value, None, int(evaluacion_id), int(user_id), int(pregunta_id))
            else:
                continue

            print(resp)
            
        for pregunta_id, textarea_value in textarea_values.items():
            if pregunta_id in textarea_values:
                textarea_value = textarea_values[pregunta_id]
                resp = respuesta_model.sudo().action_guardar_respuesta(None, textarea_value, int(evaluacion_id), int(user_id), int(pregunta_id))
            else:
                continue

            print(resp)

            


        # Redirige a la página de inicio
        # return request.redirect('/evaluacion/responder/12')
