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


@tagged("solar_project", "post_install", "-at_install")
class TestSolarDocument(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create({"name": "Doc Test Project"})
        cls.doc_type = cls.env["solar.document.type"].create(
            {"name": "Electricity Bill", "code": "bill_electricity"},
        )

    def test_document_creation(self):
        doc = self.env["solar.document"].create(
            {
                "name": "Q1 2026 Bill",
                "project_id": self.project.id,
                "document_type_id": self.doc_type.id,
            },
        )
        self.assertEqual(doc.state, "draft")
        self.assertEqual(doc.project_id, self.project)

    def test_document_approve(self):
        doc = self.env["solar.document"].create(
            {
                "name": "Site Plan",
                "project_id": self.project.id,
                "document_type_id": self.doc_type.id,
            },
        )
        doc.action_approve()
        self.assertEqual(doc.state, "approved")

    def test_document_supersede(self):
        doc_v1 = self.env["solar.document"].create(
            {
                "name": "Measurement v1",
                "project_id": self.project.id,
                "document_type_id": self.doc_type.id,
            },
        )
        doc_v2 = self.env["solar.document"].create(
            {
                "name": "Measurement v2",
                "project_id": self.project.id,
                "document_type_id": self.doc_type.id,
                "replaces_id": doc_v1.id,
            },
        )
        doc_v2.action_approve()
        self.assertEqual(doc_v1.state, "superseded")
        self.assertEqual(doc_v2.state, "approved")

    def test_project_document_count(self):
        for i in range(3):
            self.env["solar.document"].create(
                {
                    "name": f"Doc {i}",
                    "project_id": self.project.id,
                    "document_type_id": self.doc_type.id,
                },
            )
        self.assertEqual(self.project.solar_document_count, 3)


@tagged("solar_project", "post_install", "-at_install")
class TestSolarChecklist(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create({"name": "Checklist Project"})
        cls.task = cls.env["project.task"].create(
            {"name": "Site Survey", "project_id": cls.project.id},
        )

    def test_checklist_item_created(self):
        item = self.env["solar.checklist.item"].create(
            {"name": "Measure roof pitch", "task_id": self.task.id, "sequence": 1},
        )
        self.assertFalse(item.is_done)
        self.assertEqual(item.task_id, self.task)

    def test_checklist_completion(self):
        item = self.env["solar.checklist.item"].create(
            {"name": "Take photo of meter", "task_id": self.task.id},
        )
        item.is_done = True
        self.assertTrue(item.is_done)
