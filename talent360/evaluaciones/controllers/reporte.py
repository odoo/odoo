from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError

class ReporteController(http.Controller):
    @http.route(
        "/evaluacion/reporte/<model('evaluacion'):evaluacion>", type="http", auth="user"
    )
    def reporte_controler(self, evaluacion):

        if not request.env.user.has_group("evaluaciones.group_evaluaciones_cliente_cr"):
            raise AccessError("You do not have access to this resource.")

        params = evaluacion.generar_datos_reporte_generico()
        print(params)

        # Se renderiza el reporte
        return request.render("evaluaciones.encuestas_reporte", params)
