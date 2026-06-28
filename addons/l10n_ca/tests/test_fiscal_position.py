from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestFiscalPosition(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('ca')
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data['company']

    def test_domestic_fiscal_position_updates_on_state_change(self):
        ChartTemplate = self.env['account.chart.template'].with_company(self.company)

        self.company.state_id = self.env.ref('base.state_ca_on')
        self.assertEqual(self.company.domestic_fiscal_position_id, ChartTemplate.ref('fiscal_position_template_on'))

        self.company.state_id = self.env.ref('base.state_ca_qc')
        self.assertEqual(self.company.domestic_fiscal_position_id, ChartTemplate.ref('fiscal_position_template_qc'))
