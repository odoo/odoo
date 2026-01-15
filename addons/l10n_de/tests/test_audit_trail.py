from odoo.addons.account.tests.common import AccountTestInvoicingCommon, AccountTestInvoicingHttpCommon
from odoo.exceptions import UserError
from odoo.tests.common import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAuditTrailDE(AccountTestInvoicingHttpCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('de_skr03')
    def setUpClass(cls):
        super().setUpClass()

    def test_audit_trail_setting(self):
        self.assertEqual(self.env.company.country_id.code, 'DE')
        self.assertEqual(self.env.company.account_fiscal_country_id.code, 'DE')
        self.assertTrue(self.env.company.restrictive_audit_trail)
        with self.assertRaisesRegex(UserError, "Can't disable restricted audit trail: forced by localization."):
            self.env.company.restrictive_audit_trail = False
