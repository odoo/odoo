# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged('post_install', '-at_install')
class TestPosWithholdingTax(TestPoSCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.withholding_sequence = cls.env['ir.sequence'].create({
            'implementation': 'no_gap',
            'name': 'Withholding Sequence',
            'padding': 4,
            'number_increment': 1,
        })
        cls.withholding_tax = cls.env['account.tax'].create({
            'name': '10% Withholding',
            'amount_type': 'percent',
            'amount': -10.0,
            'type_tax_use': 'sale',
            'is_withholding_tax': True,
            'withholding_sequence_id': cls.withholding_sequence.id,
        })

    def _create_invoice(self, amount=1000.0):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.customer.id,
            'invoice_date': fields.Date.context_today(self.env['account.move']),
            'invoice_line_ids': [Command.create({
                'name': 'Test Product',
                'price_unit': amount,
                'tax_ids': [Command.set(self.withholding_tax.ids)],
            })],
        })
        invoice.action_post()
        return invoice

    def test_bank_payment_line_recognizes_withholding_on_full_settlement(self):
        """ A single bank payment fully settling a withholding-taxed invoice should book the
        withholding tax line (see the l10n_ph "WHT on Reconciliation/POS" gap). """
        self.basic_config.open_ui()
        session = self.basic_config.current_session_id
        invoice = self._create_invoice(1000.0)

        payment_line = self.bank_pm1._create_payment_line(
            session, 1000.0, self.customer.property_account_receivable_id, move=invoice,
        )
        payment = payment_line.payment_id
        self.assertEqual(payment.withhold, 'withhold_pay')
        self.assertTrue(
            payment.move_id.line_ids.filtered(lambda line: line.tax_line_id == self.withholding_tax),
            "the POS payment should book the withholding tax line when it fully settles the invoice",
        )

    def test_bank_payment_line_ignored_when_not_full_settlement(self):
        """ A payment that doesn't cover the full residual (e.g. a split payment, or one of
        several orders sharing a session-closing receipt) must not trigger withholding: the
        withhold-and-pay mode isn't prorate-aware and would double-count it. """
        self.basic_config.open_ui()
        session = self.basic_config.current_session_id
        invoice = self._create_invoice(1000.0)

        payment_line = self.bank_pm1._create_payment_line(
            session, 400.0, self.customer.property_account_receivable_id, move=invoice,
        )
        payment = payment_line.payment_id
        self.assertEqual(payment.withhold, 'payment')
        self.assertFalse(payment.move_id.line_ids.filtered(lambda line: line.tax_line_id == self.withholding_tax))

    def test_bank_payment_line_requires_outstanding_account(self):
        """ Withholding cannot be processed without an outstanding account configured on the
        POS payment method: this must raise a clear error rather than silently misposting. """
        self.bank_pm1.outstanding_account_id = False
        self.basic_config.open_ui()
        session = self.basic_config.current_session_id
        invoice = self._create_invoice(1000.0)

        with self.assertRaisesRegex(UserError, "Outstanding account is not set"):
            self.bank_pm1._create_payment_line(
                session, 1000.0, self.customer.property_account_receivable_id, move=invoice,
            )
