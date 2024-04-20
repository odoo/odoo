from odoo import http


class ReporteController(http.Controller):
    @http.route("/evaluacion/reporte/<model('evaluacion'):evaluacion>", type="http", auth="user")
    def reporte_controler(self, evaluacion):
        params = {
            "evaluacion": evaluacion,
            "question_and_page_data": [],
        }

        for pregunta in evaluacion.pregunta_ids:

            respuestas = []
            for respuesta in pregunta.respuesta_ids:
                respuestas.append(respuesta.respuesta_texto)

            question_data = {
                "question": pregunta,
                "respuestas": respuestas,
            }
            params["question_and_page_data"].append(question_data)
            
        # Se renderiza el reporte
        return http.request.render('evaluaciones.survey_page_statistics', params)