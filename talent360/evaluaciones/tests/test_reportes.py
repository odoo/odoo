from odoo.tests.common import TransactionCase


class TestReportes(TransactionCase):
    """
    Caso de prueba para evaluar la generación de reportes relacionados con evaluaciones en Odoo.
    """

    def setUp(self):
        """
        Inicializa el entorno de prueba antes de cada método de prueba.
        """
        super(TestReportes, self).setUp()

        # Crear una evaluación de prueba
        self.evaluacion = self.env["evaluacion"].create(
            {
                "nombre": "Evaluacion de prueba",
                "estado": "borrador",
            }
        )

        # Crear preguntas para la evaluación
        pregunta1 = self.env["pregunta"].create(
            {
                "pregunta_texto": "Pregunta 1",
                "tipo": "open_question",
            }
        )
        pregunta2 = self.env["pregunta"].create(
            {
                "pregunta_texto": "Pregunta 2",
                "tipo": "multiple_choice",
            }
        )
        pregunta3 = self.env["pregunta"].create(
            {
                "pregunta_texto": "Pregunta 3",
                "tipo": "escala",
            }
        )

        # Asignar las preguntas a la evaluación
        self.evaluacion.pregunta_ids = [
            (6, 0, [pregunta1.id, pregunta2.id, pregunta3.id])
        ]

        # Crear respuestas para las preguntas
        preguntas_respuestas = {
            pregunta1.id: [
                "Respuesta 1",
                "Respuesta 1",
                "Respuesta 1",
                "Respuesta 2",
                "Respuesta 2",
                "Respuesta 3",
                "Respuesta 3",
                "Respuesta 3",
                "Respuesta 3",
                "Respuesta 3",
            ],
            pregunta2.id: [
                "Respuesta 1",
                "Respuesta 1",
                "Respuesta 1",
                "Respuesta 2",
                "Respuesta 2",
                "Respuesta 3",
                "Respuesta 3",
                "Respuesta 3",
                "Respuesta 3",
                "Respuesta 3",
                "Respuesta 2",
                "Respuesta 3",
            ],
            pregunta3.id: [
                "5",
                "5",
                "5",
                "4",
                "4",
                "3",
                "3",
                "3",
                "3",
                "3",
                "3",
                "3",
                "3",
            ],
        }

        # Crear respuestas para las preguntas
        for pregunta, respuestas in preguntas_respuestas.items():
            for respuesta in respuestas:
                self.env["respuesta"].create(
                    {
                        "pregunta_id": pregunta,
                        "evaluacion_id": self.evaluacion.id,
                        "respuesta_texto": respuesta,
                    }
                )

    def tearDown(self):
        """
        Finaliza el entorno de prueba después de cada método de prueba.
        """
        return super().tearDown()

    def test_generar_datos_reporte_generico(self):
        """
        Prueba la generación de datos para un reporte genérico de una evaluación.

        Este método verifica que los datos generados para el reporte genérico sean correctos.
        """
        params = self.evaluacion.action_generar_datos_reporte_generico()

        # Verificar que la evaluación y el número de preguntas sean correctos
        self.assertEqual(params["evaluacion"], self.evaluacion)
        self.assertEqual(len(params["preguntas"]), 3)

        # Verificar que los datos de las preguntas sean correctos
        for pregunta in params["preguntas"]:
            if pregunta["pregunta"].tipo == "open_question":
                self.assertEqual(len(pregunta["respuestas"]), 10)
                self.assertEqual(len(pregunta["respuestas_tabuladas"]), 3)
                self.assertEqual(
                    pregunta["respuestas_tabuladas"],
                    [
                        {"texto": "Respuesta 1", "conteo": 3},
                        {"texto": "Respuesta 2", "conteo": 2},
                        {"texto": "Respuesta 3", "conteo": 5},
                    ],
                )
            elif pregunta["pregunta"].tipo == "multiple_choice":
                self.assertEqual(len(pregunta["respuestas"]), 12)
                self.assertEqual(len(pregunta["respuestas_tabuladas"]), 3)

                self.assertEqual(
                    pregunta["respuestas_tabuladas"],
                    [
                        {"texto": "Respuesta 1", "conteo": 3},
                        {"texto": "Respuesta 2", "conteo": 3},
                        {"texto": "Respuesta 3", "conteo": 6},
                    ],
                )
            elif pregunta["pregunta"].tipo == "escala":
                self.assertEqual(len(pregunta["respuestas"]), 13)
                self.assertEqual(len(pregunta["respuestas_tabuladas"]), 3)

                self.assertEqual(
                    pregunta["respuestas_tabuladas"],
                    [
                        {"texto": "5", "conteo": 3},
                        {"texto": "4", "conteo": 2},
                        {"texto": "3", "conteo": 8},
                    ],
                )
            else:
                self.fail("Tipo de pregunta no soportado")
