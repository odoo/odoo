from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError
from ..models.evaluacion import Evaluacion


class EvaluacionesController(http.Controller):
    @http.route(
        "/evaluacion/reporte/<model('evaluacion'):evaluacion>", type="http", auth="user"
    )
    def reporte_controler(self, evaluacion: Evaluacion):

        if not request.env.user.has_group(
            "evaluaciones.evaluaciones_cliente_cr_group_user"
        ):
            raise AccessError("No tienes permitido acceder a este recurso.")

        parametros = evaluacion.action_generar_datos_reporte_generico()

        # Se renderiza el reporte
        return request.render("evaluaciones.encuestas_reporte", parametros)
