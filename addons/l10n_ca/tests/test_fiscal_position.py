from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestFiscalPosition(AccountTestInvoicingCommon):

    _test_user_groups = None  # FIXME list needed groups

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

    def test_domestic_fiscal_position_without_country(self):
        fiscal_positions = self.env['account.fiscal.position'].search([
            ('company_id', '=', self.company.id),
        ])
        fiscal_positions.unlink()

        self.env['account.fiscal.position'].create({
            'name': 'Ontario',
            'company_id': self.company.id,
            'state_ids': [Command.set(self.env.ref('base.state_ca_on').ids)],
        })

        self.company.state_id = self.env.ref('base.state_ca_on')

        # No country is set on this fiscal position, so domestic_fiscal_position_id should be False
        self.assertFalse(self.company.domestic_fiscal_position_id)
