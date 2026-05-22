from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("solar_project", "post_install", "-at_install")
class TestSolarProjectBase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create({"name": "Test Solar Project"})

    def test_project_created(self):
        self.assertEqual(self.project.name, "Test Solar Project")


@tagged("solar_project", "post_install", "-at_install")
class TestSolarDocumentType(TransactionCase):
    def test_document_type_created(self):
        doc_type = self.env["solar.document.type"].create(
            {
                "name": "Electricity Bill",
                "code": "bill_electricity",
            },
        )
        self.assertEqual(doc_type.code, "bill_electricity")

    def test_document_type_code_unique(self):
        self.env["solar.document.type"].create({"name": "T1", "code": "unique_code"})
        with self.assertRaises(ValidationError):
            self.env["solar.document.type"].create(
                {"name": "T2", "code": "unique_code"},
            )


@tagged("solar_project", "post_install", "-at_install")
class TestProjectSolarExtension(TransactionCase):
    def test_solar_fields_exist(self):
        project = self.env["project.project"].create(
            {
                "name": "Solar Farm Ivanov",
                "solar_kw_capacity": 15.0,
                "solar_battery_kwh": 10.0,
                "solar_roof_type": "metal",
                "solar_grid_type": "on_grid",
            },
        )
        self.assertEqual(project.solar_kw_capacity, 15.0)
        self.assertEqual(project.solar_roof_type, "metal")

    def test_solar_stage_default(self):
        project = self.env["project.project"].create({"name": "Test"})
        self.assertEqual(project.solar_stage, "survey")

    def test_solar_coordinates(self):
        project = self.env["project.project"].create(
            {
                "name": "Geo Project",
                "solar_latitude": 50.4501,
                "solar_longitude": 30.5234,
            },
        )
        self.assertAlmostEqual(project.solar_latitude, 50.4501, places=3)
