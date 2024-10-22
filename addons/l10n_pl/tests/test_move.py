# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo import Command, fields

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountPL(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='pl'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.currency_usd = cls.env.ref('base.USD')
        cls.invoice_a = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2024-07-10',
            'currency_id': cls.currency_usd.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1.0,
                'price_unit': 1000.0,
            })],
        })

    def test_pl_out_invoice_onchange_accounting_date(self):
        self.invoice_a.delivery_date = '2024-03-31'
        self.assertEqual(self.invoice_a.date, fields.Date.to_date('2024-03-31'))
        self.assertEqual(self.invoice_a.invoice_line_ids[0].currency_rate, 1.0)

        self.env['res.currency.rate'].create({
                'name': '2024-04-28',
                'rate': 4.2799058421,
                'currency_id': self.currency_usd.id,
        })

        self.invoice_a.delivery_date = '2024-05-31'
        self.assertEqual(self.invoice_a.date, fields.Date.to_date('2024-05-31'))
        self.assertEqual(self.invoice_a.invoice_line_ids[0].currency_rate, 4.2799058421)
