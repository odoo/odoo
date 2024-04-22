from odoo import http


class ReporteController(http.Controller):
    @http.route(
        "/evaluacion/reporte/<model('evaluacion'):evaluacion>", type="http", auth="user"
    )
    def reporte_controler(self, evaluacion):
        params = {
            "evaluacion": evaluacion,
            "question_and_page_data": [],
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

            question_data = {
                "question": pregunta,
                "respuestas": respuestas,
                "respuestas_tabuladas": respuestas_tabuladas,
                "graph_data": str(respuestas_tabuladas).replace("'", '"'),
            }

            params["question_and_page_data"].append(question_data)

        # Se renderiza el reporte
        return http.request.render("evaluaciones.encuestas_reporte", params)
