from odoo.tests.common import TransactionCase
from datetime import datetime


class TestCrearEvaluacion360(TransactionCase):
    """
    Test para el método _onchange_competencia_ids del modelo Evaluacion360.
    """

    def setUp(self):
        super(TestCrearEvaluacion360, self).setUp()
        self.evaluacion360 = self.env["evaluacion"].create(
            {
                "nombre": "Evaluación 360 Test",
                "tipo": "competencia",
                "tipo_competencia": "90",
                "estado": "borrador",
                "fecha_inicio": datetime.today(),
                "fecha_final": datetime.today(),
            }
        )

    def tearDown(self):
        super(TestCrearEvaluacion360, self).tearDown()

    def crear_competencias(self):
        """
        Método para crear competencias.
        """
        competencia1 = self.env["competencia"].create(
            {
                "nombre": "Competencia 1",
                "descripcion": "Competencia 1",
            }
        )
        competencia2 = self.env["competencia"].create(
            {
                "nombre": "Competencia 2",
                "descripcion": "Competencia 2",
            }
        )
        competencia3 = self.env["competencia"].create(
            {
                "nombre": "Competencia 3",
                "descripcion": "Competencia 3",
            }
        )
        return competencia1, competencia2, competencia3

    def crear_preguntas(self):
        """
        Método para crear preguntas.
        """
        pregunta1 = self.env["pregunta"].create(
            {
                "pregunta_texto": "Pregunta 1",
                "tipo": "open_question",
            }
        )
        pregunta2 = self.env["pregunta"].create(
            {
                "pregunta_texto": "Pregunta 2",
                "tipo": "open_question",
            }
        )
        pregunta3 = self.env["pregunta"].create(
            {
                "pregunta_texto": "Pregunta 3",
                "tipo": "open_question",
            }
        )
        return pregunta1, pregunta2, pregunta3

    def relacionar_competencias_preguntas(
        self, competencia1, competencia2, competencia3, pregunta1, pregunta2, pregunta3
    ):
        """
        Método para relacionar competencias con preguntas.
        """
        competencia1.pregunta_ids = [(4, pregunta1.id)]
        competencia2.pregunta_ids = [(4, pregunta2.id)]
        competencia3.pregunta_ids = [(4, pregunta3.id)]
        return competencia1, competencia2, competencia3

    def test01_crear_evaluacion_360(self):
        """
        Test para crear una evaluación 360.
        """
        self.assertTrue(self.evaluacion360, "La evaluación no se ha creado")
        self.assertEqual(
            self.evaluacion360.nombre,
            "Evaluación 360 Test",
            "El nombre de la evaluación no es correcto",
        )
        self.assertEqual(
            self.evaluacion360.tipo,
            "competencia",
            "El tipo de la evaluación no es correcto",
        )

        self.assertEqual(
            self.evaluacion360.tipo_competencia,
            "90",
            "El tipo de competencia de la evaluación no es correcto",
        )

        self.assertEqual(
            self.evaluacion360.estado,
            "borrador",
            "El estado de la evaluación no es correcto",
        )

    def test02_agregar_competencias(self):
        """
        Test para agregar competencias a la evaluación 360.
        """
        competencia1, competencia2, competencia3 = self.crear_competencias()
        self.evaluacion360.competencia_ids = [(4, competencia1.id)]
        self.evaluacion360.competencia_ids = [(4, competencia2.id)]
        self.evaluacion360.competencia_ids = [(4, competencia3.id)]
        self.assertTrue(
            self.evaluacion360.competencia_ids, "No se han agregado competencias"
        )
        self.assertEqual(
            len(self.evaluacion360.competencia_ids),
            3,
            "No se han agregado las 3 competencias",
        )

    def test03_agregar_preguntas(self):
        """
        Test para agregar preguntas a la evaluación 360.
        """
        competencia1, competencia2, competencia3 = self.crear_competencias()
        pregunta1, pregunta2, pregunta3 = self.crear_preguntas()
        competencia1, competencia2, competencia3 = (
            self.relacionar_competencias_preguntas(
                competencia1,
                competencia2,
                competencia3,
                pregunta1,
                pregunta2,
                pregunta3,
            )
        )
        self.evaluacion360.competencia_ids = [(4, competencia1.id)]
        self.evaluacion360.competencia_ids = [(4, competencia2.id)]
        self.evaluacion360.competencia_ids = [(4, competencia3.id)]
        self.assertTrue(
            self.evaluacion360.competencia_ids.pregunta_ids,
            "No se han agregado preguntas",
        )
        self.assertEqual(
            len(self.evaluacion360.competencia_ids.pregunta_ids),
            3,
            "No se han agregado las 3 preguntas",
        )
        self.assertEqual(
            self.evaluacion360.competencia_ids.pregunta_ids[0].pregunta_texto,
            "Pregunta 1",
            "Pregunta 1 no se ha agregado correctamente",
        )
        self.assertEqual(
            self.evaluacion360.competencia_ids.pregunta_ids[1].pregunta_texto,
            "Pregunta 2",
            "Pregunta 2 no se ha agregado correctamente",
        )
        self.assertEqual(
            self.evaluacion360.competencia_ids.pregunta_ids[2].pregunta_texto,
            "Pregunta 3",
            "Pregunta 3 no se ha agregado correctamente",
        )
