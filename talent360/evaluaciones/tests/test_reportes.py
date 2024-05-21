from odoo.tests.common import TransactionCase
from datetime import datetime


class TestReportes(TransactionCase):
    """
    Caso de prueba para evaluar la generación de reportes relacionados con evaluaciones en Odoo.
    """

    def setUp(self):
        """
        Inicializa el entorno de prueba antes de cada método de prueba.
        """
        super(TestReportes, self).setUp()

        # Create a user
        user = self.env["res.users"].create(
            {
                "name": "Test User",
                "login": "testuser",
                "password": "testuser",
            }
        )

        # Create a department
        department = self.env["hr.department"].create(
            {
                "name": "Test Department",
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

        opciones = self.env["opcion"].create(
            [
                {"opcion_texto": "A", "valor": 3},
                {"opcion_texto": "B", "valor": 2},
                {"opcion_texto": "C", "valor": 1},
            ]
        )

        # Crear una evaluación de prueba
        self.evaluacion = self.env["evaluacion"].create(
            {
                "nombre": "Evaluacion de prueba",
                "estado": "borrador",
                "tipo": "CLIMA",
                "fecha_inicio": datetime.today(),
                "fecha_final": datetime.today(),
            }
        )

        preguntas = self.env["pregunta"].create(
            [
                {
                    "pregunta_texto": "Pregunta 1",
                    "tipo": "escala",
                    "ponderacion": "ascendente",
                    "categoria": "reclutamiento_y_seleccion_de_personal",
                    "respuesta_ids": [
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "1",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "1",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "2",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "2",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "2",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "3",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "3",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "3",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "3",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                    ],
                },
                {
                    "pregunta_texto": "Pregunta 2",
                    "tipo": "escala",
                    "ponderacion": "descendente",
                    "categoria": "reclutamiento_y_seleccion_de_personal",
                    "respuesta_ids": [
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "1",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "1",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "2",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "2",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "2",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "3",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "3",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "3",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "3",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                    ],
                },
                {
                    "pregunta_texto": "Pregunta 3",
                    "tipo": "multiple_choice",
                    "categoria": "formacion_y_capacitacion",
                    "opcion_ids": [(4, opcion.id) for opcion in opciones],
                    "respuesta_ids": [
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "opcion_id": opciones[0].id,
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "opcion_id": opciones[0].id,
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "opcion_id": opciones[0].id,
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "opcion_id": opciones[1].id,
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "opcion_id": opciones[1].id,
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "opcion_id": opciones[2].id,
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "opcion_id": opciones[2].id,
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "opcion_id": opciones[2].id,
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "opcion_id": opciones[2].id,
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                    ],
                },
                {
                    "pregunta_texto": "Pregunta 4",
                    "tipo": "open_question",
                    "categoria": "formacion_y_capacitacion",
                    "respuesta_ids": [
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "5",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "5",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "5",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "4",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "4",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "3",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "3",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "3",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "usuario_id": user.id,
                                "respuesta_texto": "3",
                                "evaluacion_id": self.evaluacion.id,
                            },
                        ),
                    ],
                },
            ],
        )

        self.evaluacion.write(
            {"pregunta_ids": [(4, pregunta.id) for pregunta in preguntas]}
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
        self.assertEqual(len(params["preguntas"]), 4)

        # Verificar que los datos de las preguntas sean correctos

        self.assertEqual(
            params["preguntas"][0]["respuestas_tabuladas"],
            [
                {"nombre": "Casi nunca", "valor": 2},
                {"nombre": "A veces", "valor": 3},
                {"nombre": "Casi siempre", "valor": 4},
            ],
        )

        self.assertEqual(
            params["preguntas"][1]["respuestas_tabuladas"],
            [
                {"nombre": "Casi siempre", "valor": 2},
                {"nombre": "A veces", "valor": 3},
                {"nombre": "Casi nunca", "valor": 4},
            ],
        )

        self.assertEqual(
            params["preguntas"][2]["respuestas_tabuladas"],
            [
                {"nombre": "A", "valor": 3},
                {"nombre": "B", "valor": 2},
                {"nombre": "C", "valor": 4},
            ],
        )

        self.assertEqual(
            params["preguntas"][3]["respuestas_tabuladas"],
            [
                {"nombre": "5", "valor": 3},
                {"nombre": "4", "valor": 2},
                {"nombre": "3", "valor": 4},
            ],
        )

    def test_validar_filtro(self):
        """
        Prueba la validación de un filtro.

        Este método verifica que el filtro sea válido.
        """

        datos_demograficos = {
            "departamento": "Test Department",
            "puesto": "Test Employee",
            "genero": "Masculino",
            "generacion": "Millennials",
        }

        filtro = self.evaluacion.validar_filtro(
            {
                "Departamento": {
                    "valores": ["Test Department"],
                    "categoria_interna": "departamento",
                }
            },
            datos_demograficos=datos_demograficos,
        )
        self.assertEqual(filtro, True)

        filtro = self.evaluacion.validar_filtro(
            {
                "Departamento": {
                    "valores": ["Test Department"],
                    "categoria_interna": "departamento",
                },
                "Puesto": {
                    "valores": ["Test Employee"],
                    "categoria_interna": "puesto",
                },
            },
            datos_demograficos=datos_demograficos,
        )
        self.assertEqual(filtro, True)

        filtro = self.evaluacion.validar_filtro(
            {
                "Departamento": {
                    "valores": ["Test Department"],
                    "categoria_interna": "departamento",
                },
                "Puesto": {"valores": ["Test Employee"], "categoria_interna": "puesto"},
            },
            datos_demograficos=datos_demograficos,
        )
        self.assertEqual(filtro, True)

        filtro = self.evaluacion.validar_filtro(
            {
                "Departamento": {
                    "valores": ["Test Department"],
                    "categoria_interna": "departamento",
                },
                "Puesto": {"valores": ["No valido"], "categoria_interna": "puesto"},
            },
            datos_demograficos=datos_demograficos,
        )
        self.assertEqual(filtro, False)

        filtro = self.evaluacion.validar_filtro(
            {"Departamento": {"valores": ["Test Department"], "categoria_interna": "departamento"}},
            datos_demograficos=datos_demograficos,
        )
        self.assertEqual(filtro, True)
