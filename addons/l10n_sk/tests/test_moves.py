# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import fields, Command


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountSK(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('sk')
    def setUpClass(cls):
        super().setUpClass()

        cls.invoice_a = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2024-07-10',
            'invoice_line_ids': [Command.create({
                'quantity': 1.0,
                'price_unit': 1000.0,
            })],
        })

    def test_sk_out_invoice_onchange_accounting_date(self):
        currency_usd = self.env.ref('base.USD')
        self.invoice_a.currency_id = currency_usd.id
        self.invoice_a.taxable_supply_date = '2024-03-31'
        self.assertEqual(self.invoice_a.date, fields.Date.to_date('2024-03-31'))
        self.assertEqual(self.invoice_a.invoice_currency_rate, 1.0)
        self.assertEqual(self.invoice_a.invoice_line_ids[0].currency_rate, 1.0)

        # Create rates for both the taxable supply date and the day before, to verify that the previous day's rate is fetched
        self.env['res.currency.rate'].create({
            'name': '2024-05-30',
            'rate': 0.0386,
            'currency_id': currency_usd.id,
        })
        self.env['res.currency.rate'].create({
            'name': '2024-05-31',
            'rate': 0.0387,
            'currency_id': currency_usd.id,
        })

        self.invoice_a.taxable_supply_date = '2024-05-31'
        self.assertEqual(self.invoice_a.date, fields.Date.to_date('2024-05-31'))
        self.assertEqual(self.invoice_a.invoice_currency_rate, 0.0386)
        self.assertEqual(self.invoice_a.invoice_line_ids[0].currency_rate, 0.0386)
