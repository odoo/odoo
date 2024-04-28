from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError
from ..models.evaluacion import Evaluacion


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
