from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestValidMovesDomain(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.move = cls.env["stock.move"]
        cls.company = cls.env.user.company_id

    def _domain_str(self):
        return str(self.move._get_domain_valid_moves())

    def test_anglo_saxon_excludes_reinvoiced_products(self):
        self.company.account_config_id.anglo_saxon_accounting = True
        self.assertIn("expense_policy", self._domain_str())

    def test_without_anglo_saxon_keeps_base_domain(self):
        self.company.account_config_id.anglo_saxon_accounting = False
        self.assertNotIn("expense_policy", self._domain_str())
