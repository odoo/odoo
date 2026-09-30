# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import fields, Command
from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountMoveDE(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('de_skr03')
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Helmut',
            'country_id': cls.env.ref('base.de').id,
        })

    @freeze_time('2025-01-01')
    def test_missing_invoice_delivery_date(self):
        ''' Test that confirming an Account Move sets a value for delivery_date if none present
        '''
        move = self.env['account.move'].with_context(company_id=self.company_data['company'].id).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1.0,
                'price_unit': 1000.0,
            })],
        })
        move.action_post()
        self.assertEqual(fields.Date.from_string('2025-01-01'), move.invoice_date)
        self.assertEqual(fields.Date.from_string('2025-01-01'), move.delivery_date)

    def test_out_invoice_custom_currency_rate_with_missing_delivery_date(self):

        if not self.env['ir.module.module'].search([('name', '=', 'l10n_hu_edi'), ('state', '=', 'installed')]):
            self.skipTest("This test requires the installation of the l10n_hu_edi module.")

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'currency_id': self.env['res.currency'].create({'name': "XYZ", 'symbol': 'X'}).id,
            'invoice_currency_rate': 5,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})],
        })
        expected_lines_vals = [
            {'balance': -200.0, 'amount_currency': -1000.0},
            {'balance': -38.0, 'amount_currency': -190.0},
            {'balance': 238.0, 'amount_currency': 1190.0},
        ]
        self.assertRecordValues(move.line_ids, expected_lines_vals)
        move.action_post()
        self.assertRecordValues(move.line_ids, expected_lines_vals)
