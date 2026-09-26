# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

from odoo.addons.l10n_ph.models.l10n_ph_qrph_transaction import QRPH_REUSE_SECONDS
from odoo.addons.l10n_ph.tests.common import TestPhCommon

MAYA_REQUEST = 'odoo.addons.l10n_ph.models.res_bank.ResPartnerBank._l10n_ph_qrph_make_request'
# Reaching Maya about a code that is already settled means the guard against paying twice is gone.
MAYA_SETTLED = "Maya was asked about a code that is already settled"


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPhQrph(TestPhCommon, HttpCase):
    """ QRPH codes are minted by Maya, so the point is to call them as rarely as the payment allows. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.company_data['company']
        company.qr_code = True

        cls.bank_qrph = cls.env['res.partner.bank'].create({
            'account_number': '1234567890',
            'partner_id': company.partner_id.id,
            'company_id': company.id,
            'country_id': cls.env.ref('base.ph').id,
            'l10n_ph_qrph_public_key': 'pk-test-key',
            'allow_out_payment': True,
        })
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'partner_bank_id': cls.bank_qrph.id,
            'invoice_date': '2026-09-16',
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 100})],
            'qr_code_method': 'ph_qrph',
        })
        cls.invoice.action_post()

        cls.maya_code = {
            'paymentId': 'e732f996-cb87-4120-b712-166d8183c01d',
            'redirectUrl': 'https://payments-web-sandbox.paymaya.com/v2/qr?id=e732f996',
            'qrCodeBody': 'a-qrph-payload',
        }
        cls.maya_second_code = {
            'paymentId': '23b0f938-7f47-4e2f-9a48-2f8e1c5f0d11',
            'redirectUrl': 'https://payments-web-sandbox.paymaya.com/v2/qr?id=23b0f938',
            'qrCodeBody': 'another-qrph-payload',
        }

    def test_code_is_only_minted_for_a_paying_customer(self):
        """ Rendering an invoice must not open a payment on Maya; showing it to its payer must. """
        with patch(MAYA_REQUEST, return_value=self.maya_code) as maya:
            self.assertIsNone(self.invoice._generate_qr_code())
            maya.assert_not_called()

            self.assertIsNotNone(self.invoice.with_context(is_online_qr=True)._generate_qr_code())
            maya.assert_called_once()

        transaction = self.invoice.l10n_ph_qrph_transaction_ids
        self.assertEqual(len(transaction), 1)
        self.assertEqual(transaction.maya_payment_id, self.maya_code['paymentId'])
        self.assertEqual(transaction.qr_code_body, self.maya_code['qrCodeBody'])
        self.assertEqual(transaction.state, 'pending')
        self.assertEqual(transaction.amount, 100)

    def test_code_is_reused_until_it_goes_stale(self):
        """ Refreshing the invoice must hand out the same code rather than pile up payments. """
        with patch(MAYA_REQUEST, return_value=self.maya_code) as maya:
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()
            maya.assert_called_once()

        self.assertEqual(len(self.invoice.l10n_ph_qrph_transaction_ids), 1)

        # Past the reuse window, the customer is given a fresh code. The clock is moved forward
        # rather than the creation date backwards, which the database stamps and owns.
        gone_stale = fields.Datetime.now() + timedelta(seconds=QRPH_REUSE_SECONDS + 60)
        with freeze_time(gone_stale), patch(MAYA_REQUEST, return_value=self.maya_second_code) as maya:
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()
            maya.assert_called_once()

        self.assertEqual(len(self.invoice.l10n_ph_qrph_transaction_ids), 2)
        # The next customer landing on the invoice must be given the fresh code, not the stale one.
        latest = self.env['l10n_ph.qrph.transaction']._get_latest_transaction('account.move', str(self.invoice.id))
        self.assertEqual(latest.qr_code_body, self.maya_second_code['qrCodeBody'])

    def test_unpaid_code_leaves_the_invoice_alone(self):
        with patch(MAYA_REQUEST, return_value=self.maya_code):
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()

        with patch(MAYA_REQUEST, return_value={'status': 'PENDING_PAYMENT'}):
            self.invoice.action_l10n_ph_qrph_update_payment_status()

        self.assertEqual(self.invoice.payment_state, 'not_paid')
        self.assertEqual(self.invoice.l10n_ph_qrph_transaction_ids.state, 'pending')

    def test_expired_code_is_marked_failed(self):
        with patch(MAYA_REQUEST, return_value=self.maya_code):
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()

        with patch(MAYA_REQUEST, return_value={'status': 'PAYMENT_EXPIRED'}):
            self.invoice.action_l10n_ph_qrph_update_payment_status()

        self.assertEqual(self.invoice.payment_state, 'not_paid')
        self.assertEqual(self.invoice.l10n_ph_qrph_transaction_ids.state, 'failed')

    def test_paid_code_registers_the_payment(self):
        with patch(MAYA_REQUEST, return_value=self.maya_code):
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()

        with patch(MAYA_REQUEST, return_value={'status': 'PAYMENT_SUCCESS'}):
            self.invoice.action_l10n_ph_qrph_update_payment_status()

        # The payment is registered on the invoice, which accounting then leaves 'in_payment'
        # until a bank statement matches it; what the code is responsible for is the residual.
        self.assertEqual(self.invoice.amount_residual, 0)
        self.assertTrue(self.invoice.matched_payment_ids)
        self.assertEqual(self.invoice.l10n_ph_qrph_transaction_ids.state, 'paid')
        self.assertTrue(any(
            self.maya_code['paymentId'] in (message.body or '')
            for message in self.invoice.message_ids
        ))

    def test_paid_code_settles_what_is_left_of_a_partly_paid_invoice(self):
        """ A code is minted for the residual, so an invoice already partly paid is settled too. """
        self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=self.invoice.ids,
        ).create({'amount': 40})._create_payments()
        self.assertEqual(self.invoice.payment_state, 'partial')

        with patch(MAYA_REQUEST, return_value=self.maya_code):
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()
        self.assertEqual(self.invoice.l10n_ph_qrph_transaction_ids.amount, 60)

        with patch(MAYA_REQUEST, return_value={'status': 'PAYMENT_SUCCESS'}):
            self.invoice.action_l10n_ph_qrph_update_payment_status()

        self.assertEqual(self.invoice.amount_residual, 0)
        self.assertEqual(self.invoice.l10n_ph_qrph_transaction_ids.state, 'paid')

    def test_code_needs_pesos_and_a_key(self):
        error = self.bank_qrph._get_error_messages_for_qr('ph_qrph', self.partner_a, self.env.ref('base.USD'))
        self.assertIn("currency other than PHP", error)

        self.bank_qrph.l10n_ph_qrph_public_key = False
        error = self.bank_qrph._get_error_messages_for_qr('ph_qrph', self.partner_a, self.env.ref('base.PHP'))
        self.assertIn("public key", error)

    def test_code_needs_an_amount(self):
        """ There is no amount-less QRPH code, which is what the point of sale asks for when offline. """
        with self.assertRaises(UserError):
            self.bank_qrph.build_qr_code_value(
                0, 'a reference', '', self.env.ref('base.PHP'), self.partner_a, 'ph_qrph', silent_errors=False,
            )

    def test_webhook_settles_once_and_the_repeat_changes_nothing(self):
        """ Maya repeats a notification it was given no answer to, which must not pay twice. """
        with patch(MAYA_REQUEST, return_value=self.maya_code):
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()

        with patch(MAYA_REQUEST, return_value={'status': 'PAYMENT_SUCCESS'}):
            self._notify_webhook(self.maya_code['paymentId'])
        payments = self.invoice.matched_payment_ids
        self.assertEqual(len(payments), 1)
        self.assertEqual(self.invoice.amount_residual, 0)

        # The repeat must not even reach Maya: the code is spent, whatever Maya still says about it.
        with patch(MAYA_REQUEST, side_effect=AssertionError(MAYA_SETTLED)):
            response = self._notify_webhook(self.maya_code['paymentId'])
        self.assertEqual(response.status_code, 200, "Maya keeps retrying a notification it gets no 200 for")
        self.assertEqual(self.invoice.matched_payment_ids, payments)

    def test_webhook_ignores_a_code_it_knows_nothing_about(self):
        """ The route is public, so a made-up notification must come to nothing. """
        with patch(MAYA_REQUEST, side_effect=AssertionError("Maya was asked about a code we never minted")):
            response = self._notify_webhook('never minted by us')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.invoice.matched_payment_ids)

    def test_undone_payment_is_not_paid_again_by_the_same_code(self):
        """ A code pays an invoice once: undoing that payment must not have the cron redo it. """
        with patch(MAYA_REQUEST, return_value=self.maya_code):
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()
        with patch(MAYA_REQUEST, return_value={'status': 'PAYMENT_SUCCESS'}):
            self.invoice.action_l10n_ph_qrph_update_payment_status()
        self.assertEqual(self.invoice.amount_residual, 0)

        # An accountant who unreconciles the payment puts the invoice back in the cron's way.
        self.invoice.line_ids.remove_move_reconcile()
        self.assertEqual(self.invoice.payment_state, 'not_paid')

        payments_before = self.env['account.payment'].search([])
        with patch(MAYA_REQUEST, side_effect=AssertionError(MAYA_SETTLED)):
            self.env['account.move']._l10n_ph_qrph_cron_update_payment_status()
        self.assertEqual(self.env['account.payment'].search([]), payments_before)

    @mute_logger('odoo.addons.l10n_ph.models.l10n_ph_qrph_transaction')
    def test_code_settles_only_what_it_covers(self):
        """ Maya cannot take a code back, so one minted for less must not buy what costs more.

        This is what a self-order kiosk leans on: a customer who is handed a code, goes back to
        their order and adds to it can otherwise pay the order they ended up with at the price of
        the one they started from.
        """
        with patch(MAYA_REQUEST, return_value=self.maya_code):
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()
        transaction = self.invoice.l10n_ph_qrph_transaction_ids
        self.assertEqual(transaction.amount, 100)

        with patch(MAYA_REQUEST, return_value={'status': 'PAYMENT_SUCCESS'}):
            self.assertFalse(transaction._get_paid_transaction(140), "a code minted for 100 does not settle 140")
        self.assertEqual(transaction.state, 'paid', "the money did reach Maya, and the merchant has to see it")
        self.assertFalse(transaction.settled_date)

        self.assertEqual(transaction._get_paid_transaction(100), transaction, "it does settle what it was minted for")
        self.assertEqual(transaction._get_paid_transaction(60), transaction, "and anything it covers")

    def _notify_webhook(self, maya_payment_id=None, body=None):
        """ Post to the public webhook the way Maya does, and return the response. """
        if body is None:
            body = json.dumps({'id': maya_payment_id})
        response = self.url_open('/l10n_ph/qrph/webhook', data=body, headers={'Content-Type': 'application/json'})
        self.env.invalidate_all()  # the request ran in its own environment
        return response
