from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError
from ..models.evaluacion import Evaluacion
from ..models.respuesta import Respuesta as respuesta
from ..models.pregunta import Pregunta as pregunta
import json
from ..models.usuario_evaluacion_rel import UsuarioEvaluacionRel as usuario_evaluacion
import time
import werkzeug


class EvaluacionesController(http.Controller):
    """Controlador para manejar las solicitudes relacionadas con las evaluaciones."""

    @http.route(
        "/evaluacion/reporte/<model('evaluacion'):evaluacion>", type="http", auth="user"
    )
    def reporte_controller(self, evaluacion: Evaluacion):
        """Método para generar y mostrar un reporte de evaluación.
        Este método verifica que el usuario tenga los permisos necesario, obtiene los datos
        del modelo de evaluaciones y renderiza el reporte con esos datos.

        :return: html renderizado del template con los datos del reporte
        """

        if not request.env.user.has_group(
            "evaluaciones.evaluaciones_cliente_cr_group_user"
        ):
            raise AccessError(_("No tienes permitido acceder a este recurso."))

        parametros = evaluacion.generar_datos_reporte_NOM_035_action()

        return request.render("evaluaciones.encuestas_reporte", parametros)

    @http.route(
        "/evaluacion/responder/<int:evaluacion_id>/<string:token>",
        type="http",
        auth="public",
        website=True,
    )
    def responder_evaluacion_controller(self, evaluacion_id, token):
        """Método para desplegar el formulario de permitir al usuario responder una evaluación.
        Este método verifica que el usuario tenga los permisos necesario, obtiene los datos
        del modelo de evaluaciones y renderiza el formulario con esos datos.

        :return: html renderizado del template con los datos del formulario
        """
        usuario_eva_mod = request.env["usuario.evaluacion.rel"]

        evaluacion = request.env["evaluacion"].sudo().browse(evaluacion_id)

        if request.env.user != request.env.ref("base.public_user"):
            usuario_eval_relacion = usuario_eva_mod.sudo().search(
                [
                    ("usuario_id.id", "=", request.env.user.id),
                    ("evaluacion_id.id", "=", evaluacion.id),
                    ("token", "=", token),
                ]
            )

        else:
            usuario_eval_relacion = usuario_eva_mod.sudo().search(
                [
                    # ("evaluacion_id", "=", evaluacion.id),
                    ("token", "=", token)
                ]
            )

        if not usuario_eval_relacion:
            return request.render("evaluaciones.evaluacion_responder_form_draft")

        # Obtén la evaluación basada en el ID
        parametros = evaluacion.get_evaluaciones_action(evaluacion_id)

        if request.env.user != request.env.ref("base.public_user"):
            parametros["contestada"] = usuario_eva_mod.sudo().action_get_estado(
                request.env.user.id, evaluacion_id, None
            )

        else:
            parametros["contestada"] = usuario_eva_mod.sudo().action_get_estado(
                None, evaluacion_id, token
            )

        parametros["token"] = token

        # Renderiza la plantilla con la evaluación
        return request.render("evaluaciones.evaluaciones_responder", parametros)

    @http.route("/evaluacion/contestada", type="http", auth="public", website=True)
    def evaluacion_contestada_controller(self, **post):
        """Método para desplegar un mensaje de que la evaluación ya fue contestada.
        Este método renderiza un mensaje indicando que la evaluación ya fue contestada.

        :return: html renderizado del template con el mensaje
        """

        return request.render("evaluaciones.evaluacion_responder_form_done")

    @http.route(
        "/evaluacion/responder",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
        csrf=False,
    )
    def responder_evaluacion_controller_post(self, **post):
        """Método para procesar la respuesta del formulario de evaluación.
        Este método verifica que el usuario tenga los permisos necesario, obtiene los datos
        del modelo de evaluaciones y guarda la respuesta del usuario.

        :return: redirección a la página de inicio
        """

        user = None

        if request.env.user != request.env.ref("base.public_user"):
            if not request.env.user.has_group(
                "evaluaciones.evaluaciones_cliente_cr_group_user"
            ):
                raise AccessError(_("No tienes permitido acceder a este recurso."))

            user = request.env.user.id

        post_data = json.loads(request.httprequest.data)

        valores_radios = post_data.get("radioValues")
        valores_radios_escala = post_data.get("radioValuesScale")
        valores_textarea = post_data.get("textareaValues")
        evaluacion_id = post_data.get("evaluacion_id")
        usuario_id = user
        respuesta_modelo = request.env["respuesta"]
        token = post_data.get("token")

        for pregunta_id, valor_radio in valores_radios.items():
            if pregunta_id in valores_radios:
                valor_radio = valores_radios[pregunta_id]
                if request.env.user != request.env.ref("base.public_user"):
                    resp = respuesta_modelo.sudo().guardar_respuesta_action(
                        valor_radio,
                        None,
                        int(evaluacion_id),
                        int(usuario_id),
                        int(pregunta_id),
                        None,
                        False,
                    )
                else:
                    resp = respuesta_modelo.sudo().guardar_respuesta_action(
                        valor_radio,
                        None,
                        int(evaluacion_id),
                        None,
                        int(pregunta_id),
                        token,
                        False,
                    )
            else:
                continue

        for pregunta_id, valor_textarea in valores_textarea.items():
            if pregunta_id in valores_textarea:
                valor_textarea = valores_textarea[pregunta_id]
                if request.env.user != request.env.ref("base.public_user"):
                    resp = respuesta_modelo.sudo().guardar_respuesta_action(
                        None,
                        valor_textarea,
                        int(evaluacion_id),
                        int(usuario_id),
                        int(pregunta_id),
                        None,
                        False,
                    )
                else:
                    resp = respuesta_modelo.sudo().guardar_respuesta_action(
                        None,
                        valor_textarea,
                        int(evaluacion_id),
                        None,
                        int(pregunta_id),
                        token,
                        False,
                    )
            else:
                continue

        for pregunta_id, valor_radio in valores_radios_escala.items():
            if pregunta_id in valores_radios_escala:
                valor_radio = valores_radios_escala[pregunta_id]
                if request.env.user != request.env.ref("base.public_user"):
                    resp = respuesta_modelo.sudo().guardar_respuesta_action(
                        valor_radio,
                        None,
                        int(evaluacion_id),
                        int(usuario_id),
                        int(pregunta_id),
                        None,
                        True,
                    )
                else:
                    resp = respuesta_modelo.sudo().guardar_respuesta_action(
                        valor_radio,
                        None,
                        int(evaluacion_id),
                        None,
                        int(pregunta_id),
                        token,
                        True,
                    )
            else:
                continue

        # Actualiza el estado de la evaluación para el usuario
        usuario_eva_mod = request.env["usuario.evaluacion.rel"]

        if request.env.user != request.env.ref("base.public_user"):
            usuario_eva_mod.sudo().action_update_estado(usuario_id, evaluacion_id, None)
        else:
            usuario_eva_mod.sudo().action_update_estado(None, evaluacion_id, token)

        return werkzeug.utils.redirect("/evaluacion/contestada")

    @http.route(
        "/evaluacion/reporte-clima/<model('evaluacion'):evaluacion>",
        type="http",
        auth="user",
    )
    def reporte_clima_controller(self, evaluacion: Evaluacion):
        """Método para generar y mostrar el reporte de clima laboral.
        :return: HTML renderizado del template con los datos del reporte.
        """

        # Verificar permisos de usuario
        if not request.env.user.has_group(
            "evaluaciones.evaluaciones_cliente_cr_group_user"
        ):
            raise AccessError(_("No tienes permitido acceder a este recurso."))

        # Generar parámetros para el reporte
        parametros = evaluacion.action_generar_datos_reporte_clima()

        return request.render("evaluaciones.encuestas_reporte_clima", parametros)
