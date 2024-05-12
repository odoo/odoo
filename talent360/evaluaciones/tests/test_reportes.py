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
                "tipo": "escala",
                "categoria": "reclutamiento_y_seleccion_de_personal",
            }
        )
        pregunta2 = self.env["pregunta"].create(
            {
                "pregunta_texto": "Pregunta 2",
                "tipo": "escala",
                "categoria": "reclutamiento_y_seleccion_de_personal",
            }
        )
        pregunta3 = self.env["pregunta"].create(
            {
                "pregunta_texto": "Pregunta 3",
                "tipo": "escala",
                "categoria": "formacion_y_capacitacion",
            }
        )

        # Asignar las preguntas a la evaluación
        self.evaluacion.pregunta_ids = [
            (6, 0, [pregunta1.id, pregunta2.id, pregunta3.id])
        ]

        # Crear respuestas para las preguntas
        preguntas_respuestas = {
            pregunta1.id: [
                "1",
                "1",
                "1",
                "2",
                "2",
                "3",
                "3",
                "3",
                "3",
                "3",
            ],
            pregunta2.id: [
                "1",
                "1",
                "1",
                "2",
                "2",
                "3",
                "3",
                "3",
                "3",
                "3",
                "2",
                "3",
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

        # Create a department
        department = self.env["hr.department"].create(
            {
                "name": "Test Department",
            }
        )

        # Create a user
        user = self.env["res.users"].create(
            {
                "name": "Test User",
                "login": "testuser",
                "password": "testuser",
            }
        )

        # Create an employee linked to the user and department
        employee = self.env["hr.employee"].create(
            {
                "name": "Test Employee",
                "user_id": user.id,
                "department_id": department.id,
            }
        )

        # Crear respuestas para las preguntas
        for pregunta, respuestas in preguntas_respuestas.items():
            for respuesta in respuestas:
                self.env["respuesta"].create(
                    {
                        "pregunta_id": pregunta,
                        "evaluacion_id": self.evaluacion.id,
                        "respuesta_texto": respuesta,
                        "usuario_id": user.id,
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
        params = self.evaluacion.generar_datos_reporte_generico_action()

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
                        {"nombre": "1", "valor": 3},
                        {"nombre": "2", "valor": 2},
                        {"nombre": "3", "valor": 5},
                    ],
                )
            elif pregunta["pregunta"].tipo == "multiple_choice":
                self.assertEqual(len(pregunta["respuestas"]), 12)
                self.assertEqual(len(pregunta["respuestas_tabuladas"]), 3)

                self.assertEqual(
                    pregunta["respuestas_tabuladas"],
                    [
                        {"texto": "1", "conteo": 3},
                        {"texto": "2", "conteo": 3},
                        {"texto": "3", "conteo": 6},
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
