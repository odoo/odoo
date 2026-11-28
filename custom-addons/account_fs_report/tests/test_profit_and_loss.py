from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestProfitAndLoss(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env['fs.report'].search([('code', '=', 'PL')], limit=1)

    def _options(self, date_from, date_to):
        return {
            'company_ids': self.env.company.ids,
            'target_move': 'posted',
            'journal_ids': [],
            'date': {
                'string': date_to,
                'date_from': date_from,
                'date_to': date_to,
                'period_type': 'custom',
            },
            'columns': [{
                'label': date_to,
                'date_from': date_from,
                'date_to': date_to,
            }],
        }

    def test_pl_line_codes_and_levels(self):
        self.assertTrue(self.report)
        self.assertEqual(self.report.report_type, 'period')
        by_code = {line.code: line for line in self.report.line_ids}
        self.assertEqual(by_code['GRP'].hierarchy_level, 0)
        self.assertEqual(by_code['NEP'].hierarchy_level, 0)
        self.assertEqual(by_code['REV'].hierarchy_level, 1)
        self.assertEqual(by_code['REV'].sign, -1)
        self.assertFalse(by_code['COS'].green_on_positive)
        self.assertFalse(by_code['EXP'].green_on_positive)
        self.assertFalse(by_code['OEXP'].green_on_positive)

    def test_pl_revenue_and_net_profit(self):
        self.init_invoice(
            'out_invoice',
            partner=self.partner_a,
            invoice_date='2026-06-15',
            post=True,
            amounts=[1000.0],
        )
        data = self.env['fs.report.engine'].get_report_data(
            self.report.id,
            self._options('2026-01-01', '2026-12-31'),
        )
        amounts = {row['code']: row['columns'][0] for row in data['lines']}
        self.assertAlmostEqual(amounts['REV'], 1000.0)
        self.assertAlmostEqual(amounts['GRP'], 1000.0)
        self.assertAlmostEqual(amounts['NEP'], 1000.0)
        levels = {row['code']: row['level'] for row in data['lines']}
        self.assertEqual(levels['NEP'], 0)
        self.assertEqual(levels['REV'], 1)
