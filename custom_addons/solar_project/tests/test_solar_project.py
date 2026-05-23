from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("solar_project", "post_install", "-at_install")
class TestSolarProjectBase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create({"name": "Test Solar Project"})

    def test_solar_fields_attached_to_project(self):
        """Module-specific assertion: project.project has solar_stage default 'survey' from solar_project."""
        self.assertEqual(self.project.solar_stage, "survey")
        self.assertIn("solar_kw_capacity", self.project._fields)
        self.assertIn("solar_document_ids", self.project._fields)


@tagged("solar_project", "post_install", "-at_install")
class TestSolarDocumentType(TransactionCase):
    def test_document_type_created(self):
        doc_type = self.env["solar.document.type"].create(
            {
                "name": "Test Doc Type",
                "code": "test_doc_type_a",
            },
        )
        self.assertEqual(doc_type.code, "test_doc_type_a")

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
            {"name": "Test Doc Type", "code": "test_doc_type_for_docs"},
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
        item.write({"is_done": True})
        item.invalidate_recordset()
        self.assertTrue(item.is_done)


@tagged("solar_project", "post_install", "-at_install")
class TestSolarDocumentTypeData(TransactionCase):
    def test_demo_types_loaded(self):
        bill_type = self.env.ref(
            "solar_project.solar_dtype_bill_electricity",
            raise_if_not_found=False,
        )
        self.assertTrue(
            bill_type,
            "Demo document type solar_dtype_bill_electricity not loaded "
            "(env.ref returned False)",
        )
        self.assertEqual(bill_type.code, "bill_electricity")

    def test_module_loaded_12_types(self):
        """Assert this module's data file loaded all 12 records by xml-id existence."""
        expected_xmlids = [
            "solar_project.solar_dtype_bill_electricity",
            "solar_project.solar_dtype_roof_measurement",
            "solar_project.solar_dtype_site_plan",
            "solar_project.solar_dtype_topographic",
            "solar_project.solar_dtype_client_brief",
            "solar_project.solar_dtype_equipment_spec",
            "solar_project.solar_dtype_single_line_diagram",
            "solar_project.solar_dtype_permit",
            "solar_project.solar_dtype_handover_act",
            "solar_project.solar_dtype_commissioning_report",
            "solar_project.solar_dtype_structural_calculation",
            "solar_project.solar_dtype_grid_connection_agreement",
        ]
        for xmlid in expected_xmlids:
            rec = self.env.ref(xmlid, raise_if_not_found=False)
            self.assertTrue(rec, f"Demo record {xmlid} not loaded")
