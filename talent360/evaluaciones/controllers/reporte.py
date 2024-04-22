from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError

class ReporteController(http.Controller):
    @http.route(
        "/evaluacion/reporte/<model('evaluacion'):evaluacion>", type="http", auth="user"
    )
    def reporte_controler(self, evaluacion):

        if not request.env.user.has_group('your_module.your_group'):
            raise AccessError("You do not have access to this resource.")


        params = {
            "evaluacion": evaluacion,
            "preguntas": [],
        }

        respuesta_tabulada = {}

        for pregunta in evaluacion.pregunta_ids:

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

            params["preguntas"].append(datos_pregunta)

        # Se renderiza el reporte
        return request.render("evaluaciones.encuestas_reporte", params)
