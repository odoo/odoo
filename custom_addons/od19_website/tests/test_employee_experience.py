from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestEmployeeExperiencePlaceholder(TransactionCase):
    def test_placeholder(self):
        self.assertTrue(True)
