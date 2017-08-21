from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests import tagged


@tagged('post_install','-at_install')
class TestManualReconciliation(AccountingTestCase):

    def test_reconciliation_proposition(self):
        pass

    def test_full_reconcile(self):
        pass

    def test_partial_reconcile(self):
        pass

    def test_reconcile_with_write_off(self):
        pass
