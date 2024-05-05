from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError
from ..models.evaluacion import Evaluacion
from ..models.respuesta import Respuesta as respuesta
from ..models.pregunta import Pregunta as pregunta
import json
from ..models.usuario_evaluacion_rel import UsuarioEvaluacionRel as usuario_evaluacion
import werkzeug


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
        "/evaluacion/responder/<int:evaluacion_id>/<string:token>", type="http", auth="public", website=True
    )
    def responder_evaluacion_controller(self, evaluacion_id, token):
        """Método para desplegar el formulario de permitir al usuario responder una evaluación.
        Este método verifica que el usuario tenga los permisos necesario, obtiene los datos
        del modelo de evaluaciones y renderiza el formulario con esos datos.

        :return: html renderizado del template con los datos del formulario
        """
        usuario_eva_mod = request.env["usuario.evaluacion.rel"]

        evaluacion = request.env["evaluacion"].sudo().browse(evaluacion_id)

        if request.env.user != request.env.ref('base.public_user'):
            user_eval_relation = usuario_eva_mod.sudo().search([
                ("usuario_id", "=", request.env.user.id),
                ("evaluacion_id", "=", evaluacion.id),
                ("token", "=", token)
            ])

        else:
            user_eval_relation = usuario_eva_mod.sudo().search([
            # ("evaluacion_id", "=", evaluacion.id),
            ("token", "=", token)
        ])
        
        
        if not user_eval_relation:
            return request.render("evaluaciones.evaluacion_responder_form_draft")

        # Obtén la evaluación basada en el ID
        parametros = evaluacion.action_get_evaluaciones(evaluacion_id)
        
        if request.env.user != request.env.ref('base.public_user'):
            parametros["contestada"] = usuario_eva_mod.sudo().action_get_estado(request.env.user.id, evaluacion_id, None)
        
        else:
            parametros["contestada"] = usuario_eva_mod.sudo().action_get_estado(None, evaluacion_id, token)
        
        parametros["token"] = token

        # Renderiza la plantilla con la evaluación
        return request.render("evaluaciones.evaluaciones_responder", parametros)
    
    @http.route(
        "/evaluacion/responder", type="http", auth="public", website=True, methods=["POST"], csrf=False
    )
    def responder_evaluacion_controller_post(self, **post):
        """Método para procesar la respuesta del formulario de evaluación.
        Este método verifica que el usuario tenga los permisos necesario, obtiene los datos
        del modelo de evaluaciones y guarda la respuesta del usuario.

        :return: redirección a la página de inicio
        """

        user = None

        if request.env.user != request.env.ref('base.public_user'):
            if not request.env.user.has_group(
                "evaluaciones.evaluaciones_cliente_cr_group_user"
            ):
                raise AccessError("No tienes permitido acceder a este recurso.")
            
            user = request.env.user.id
        
        post_data = json.loads(request.httprequest.data)

        radio_values = post_data.get("radioValues")
        radio_values_scale = post_data.get("radioValuesScale")
        textarea_values = post_data.get("textareaValues")
        evaluacion_id = post_data.get("evaluacion_id")
        user_id = user
        respuesta_model = request.env["respuesta"]
        token = post_data.get("token")

        for pregunta_id, radio_value in radio_values.items():
            if pregunta_id in radio_values:
                radio_value = radio_values[pregunta_id]
                if request.env.user != request.env.ref('base.public_user'):
                    resp = respuesta_model.sudo().action_guardar_respuesta(radio_value, None, int(evaluacion_id), int(user_id), int(pregunta_id), None, False)
                else:
                    resp = respuesta_model.sudo().action_guardar_respuesta(radio_value, None, int(evaluacion_id), None, int(pregunta_id), token, False)
            else:
                continue
            
        for pregunta_id, textarea_value in textarea_values.items():
            if pregunta_id in textarea_values:
                textarea_value = textarea_values[pregunta_id]
                if request.env.user != request.env.ref('base.public_user'):
                    resp = respuesta_model.sudo().action_guardar_respuesta(None, textarea_value, int(evaluacion_id), int(user_id), int(pregunta_id), None, False)
                else:
                    resp = respuesta_model.sudo().action_guardar_respuesta(None, textarea_value, int(evaluacion_id), None, int(pregunta_id), token, False)
            else:
                continue

        for pregunta_id, radio_value in radio_values_scale.items():
            if pregunta_id in radio_values_scale:
                radio_value = radio_values_scale[pregunta_id]
                if request.env.user != request.env.ref('base.public_user'):
                    resp = respuesta_model.sudo().action_guardar_respuesta(radio_value, None, int(evaluacion_id), int(user_id), int(pregunta_id), None, True)
                else:
                    resp = respuesta_model.sudo().action_guardar_respuesta(radio_value, None, int(evaluacion_id), None, int(pregunta_id), token, True)
            else:
                continue

        # Actualiza el estado de la evaluación para el usuario
        usuario_eva_mod = request.env["usuario.evaluacion.rel"]

        if request.env.user != request.env.ref('base.public_user'):
            usuario_eva_mod.sudo().action_update_estado(user_id, evaluacion_id, None)
        else:
            usuario_eva_mod.sudo().action_update_estado(None, evaluacion_id, token)

        # Redirige a la página de inicio
        return werkzeug.utils.redirect('/evaluacion/responder/' + str(evaluacion_id) + '/' + token, 303)
