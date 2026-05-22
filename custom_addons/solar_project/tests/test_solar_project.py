from odoo.tests import TransactionCase, tagged


@tagged("solar_project", "post_install", "-at_install")
class TestSolarProjectBase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create({"name": "Test Solar Project"})

    def test_project_created(self):
        self.assertEqual(self.project.name, "Test Solar Project")
