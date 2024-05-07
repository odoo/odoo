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

        opciones_texto = ["Respuesta 1", "Respuesta 2", "Respuesta 3"]

        opciones = {}
        for opcion in opciones_texto:
            opcion_db = self.env["opcion"].create(
                {
                    "opcion_texto": opcion,
                    "pregunta_id": pregunta2.id,
                    "valor": int(opcion.split(" ")[-1]),
                }
            )
            opciones[opcion] = opcion_db

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
                "4",
                "4",
                "4",
                "3",
                "3",
                "2",
                "2",
                "2",
                "2",
                "2",
                "2",
                "2",
                "2",
            ],
        }

        # Crear respuestas para las preguntas
        for pregunta, respuestas in preguntas_respuestas.items():
            tipo = self.env["pregunta"].browse(pregunta).tipo

            if tipo == "multiple_choice":
                for respuesta in respuestas:
                    self.env["respuesta"].create(
                        {
                            "pregunta_id": pregunta,
                            "evaluacion_id": self.evaluacion.id,
                            "opcion_id": opciones[respuesta].id,
                        }
                    )
            else:
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
                        {"nombre": "Respuesta 1", "valor": 3},
                        {"nombre": "Respuesta 2", "valor": 2},
                        {"nombre": "Respuesta 3", "valor": 5},
                    ],
                )
            elif pregunta["pregunta"].tipo == "multiple_choice":
                self.assertEqual(len(pregunta["respuestas"]), 12)
                self.assertEqual(len(pregunta["respuestas_tabuladas"]), 3)

                self.assertEqual(
                    pregunta["respuestas_tabuladas"],
                    [
                        {"nombre": "Respuesta 1", "valor": 3},
                        {"nombre": "Respuesta 2", "valor": 3},
                        {"nombre": "Respuesta 3", "valor": 6},
                    ],
                )
            elif pregunta["pregunta"].tipo == "escala":
                self.assertEqual(len(pregunta["respuestas"]), 13)
                self.assertEqual(len(pregunta["respuestas_tabuladas"]), 3)

                self.assertEqual(
                    pregunta["respuestas_tabuladas"],
                    [
                        {"nombre": "Siempre", "valor": 3},
                        {"nombre": "Casi siempre", "valor": 2},
                        {"nombre": "A veces", "valor": 8},
                    ],
                )
            else:
                self.fail("Tipo de pregunta no soportado")
