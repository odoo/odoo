from odoo.addons.hr_payroll.tests.common_payment_report import TestPaymentReportBase
from odoo.tests.common import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPaymentReportAU(TestPaymentReportBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({
            'country_id': cls.env.ref('base.au').id,
        })

    def test_payslip_payment_report_default(self):
        action = self.payslip.with_company(self.company).action_payslip_payment_report()
        self.assertEqual(
            action['context']['default_export_format'],
            'aba',
        )

    def test_payrun_payment_report_default(self):
        action = self.payrun.with_company(self.company).action_payment_report()
        self.assertEqual(
            action['context']['default_export_format'],
            'aba',
        )
