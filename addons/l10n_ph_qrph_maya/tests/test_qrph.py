# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time
from lxml import html

from odoo import fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger

from odoo.addons.l10n_ph.tests.common import TestPhCommon
from odoo.addons.l10n_ph_qrph_maya import const
from odoo.addons.l10n_ph_qrph_maya.models.l10n_ph_qrph_transaction import REUSE_SECONDS
from odoo.addons.l10n_ph_qrph_maya.models.res_bank import MayaRequestError

MAYA_REQUEST = 'odoo.addons.l10n_ph_qrph_maya.models.res_bank.ResPartnerBank._l10n_ph_qrph_make_request'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPhQrph(TestPhCommon):
    """ QRPH codes are minted by Maya, so the point is to call them as rarely as the payment allows. """

    @mute_logger('odoo.addons.base.models.ir_cron')
    def _run_cron(self):
        """ Run the cron as the scheduler would, in its own transaction, as it commits its progress. """
        cron = self.env.ref('l10n_ph_qrph_maya.ir_cron_l10n_ph_qrph_update_payment_status')
        with self.registry_test_mode():
            cron.sudo().method_direct_trigger()

    @staticmethod
    def _maya_answering(code, status='PENDING_PAYMENT'):
        """ A Maya that hands out ``code`` when asked for one, and reports ``status`` when asked about one. """
        def request(endpoint, payload=None):
            return code if payload else {'status': status}
        return request

    @staticmethod
    def _count_minted_codes(maya):
        return sum(1 for call in maya.call_args_list if call.kwargs.get('payload'))

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
            'qr_code_method': const.QR_METHOD,
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

    @mute_logger('odoo.addons.l10n_ph_qrph_maya.models.account_move')
    def test_invoice_is_shown_without_a_code_when_maya_fails(self):
        """ The bank account is on the invoice for manual payments, so a Maya outage must not block it. """
        with patch(MAYA_REQUEST, side_effect=MayaRequestError("Could not establish a connection")):
            self.assertIsNone(self.invoice.with_context(is_online_qr=True)._generate_qr_code())
        self.assertFalse(self.invoice.l10n_ph_qrph_transaction_ids)

    def test_code_belongs_to_the_company_of_the_invoice(self):
        """ The company of a bank account only limits its use, so it is not the owner of what it is paid with. """
        self.bank_qrph.company_id = False
        with patch(MAYA_REQUEST, return_value=self.maya_code):
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()
        self.assertEqual(self.invoice.l10n_ph_qrph_transaction_ids.company_id, self.invoice.company_id)

    def test_code_is_reused_until_it_goes_stale(self):
        """ Refreshing the invoice must hand out the same code rather than pile up payments. """
        with patch(MAYA_REQUEST, side_effect=self._maya_answering(self.maya_code)) as maya:
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()
            self.assertEqual(self._count_minted_codes(maya), 1)

        self.assertEqual(len(self.invoice.l10n_ph_qrph_transaction_ids), 1)

        # Past the reuse window, the customer is given a fresh code. The clock is moved forward
        # rather than the creation date backwards, which the database stamps and owns.
        gone_stale = fields.Datetime.now() + timedelta(seconds=REUSE_SECONDS + 60)
        with freeze_time(gone_stale), patch(
            MAYA_REQUEST, side_effect=self._maya_answering(self.maya_second_code),
        ) as maya:
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()
            self.assertEqual(self._count_minted_codes(maya), 1)

        self.assertEqual(len(self.invoice.l10n_ph_qrph_transaction_ids), 2)
        # The next customer landing on the invoice must be given the fresh code, not the stale one.
        latest = self.env['l10n_ph.qrph.transaction']._get_latest_transaction(
            'account.move', str(self.invoice.id), self.invoice.company_id.id,
        )
        self.assertEqual(latest.qr_code_body, self.maya_second_code['qrCodeBody'])

    def test_code_is_not_reused_for_another_bank_account(self):
        """ A code pays the account it was minted for: the invoice changing account needs a new one. """
        other_bank = self.bank_qrph.copy({'account_number': '1122334455', 'l10n_ph_qrph_public_key': 'pk-other-key'})
        with patch(MAYA_REQUEST, side_effect=self._maya_answering(self.maya_code)):
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()

        self.invoice.partner_bank_id = other_bank
        with patch(MAYA_REQUEST, side_effect=self._maya_answering(self.maya_second_code)) as maya:
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()
            self.assertEqual(self._count_minted_codes(maya), 1)

        self.assertEqual(self.invoice.l10n_ph_qrph_transaction_ids.mapped('bank_id'), self.bank_qrph | other_bank)

    def test_invoice_whose_stale_code_was_paid_is_not_given_a_new_one(self):
        """ A customer who scanned the code as it went stale has paid: show the invoice paid, not a new code. """
        with patch(MAYA_REQUEST, return_value=self.maya_code):
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()

        gone_stale = fields.Datetime.now() + timedelta(seconds=REUSE_SECONDS + 60)
        with freeze_time(gone_stale), patch(
            MAYA_REQUEST, side_effect=self._maya_answering(self.maya_second_code, status='PAYMENT_SUCCESS'),
        ) as maya:
            qr_code = self.invoice.with_context(is_online_qr=True)._generate_qr_code()

        self.assertEqual(self._count_minted_codes(maya), 0)
        self.assertFalse(qr_code)
        self.assertEqual(self.invoice.payment_state, self.invoice._get_invoice_in_payment_state())
        self.assertEqual(len(self.invoice.l10n_ph_qrph_transaction_ids), 1)

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
        transaction = self.invoice.l10n_ph_qrph_transaction_ids
        links = [
            (link.get('data-oe-model'), link.get('data-oe-id'), link.text)
            for message in self.invoice.message_ids if message.body
            for link in html.fromstring(f"<div>{message.body}</div>").iter('a')
        ]
        self.assertIn(
            ('l10n_ph.qrph.transaction', str(transaction.id), self.maya_code['paymentId']),
            links,
            "the log must link to the transaction",
        )

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

    def test_paid_code_does_not_settle_more_than_it_covers(self):
        """ A code minted for what was left to pay must not settle the invoice if that grew back. """
        self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=self.invoice.ids,
        ).create({'amount': 40})._create_payments()
        with patch(MAYA_REQUEST, return_value=self.maya_code):
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()
        self.assertEqual(self.invoice.l10n_ph_qrph_transaction_ids.amount, 60)

        # The first payment is undone: 100 is due again, and the code only covers 60.
        self.invoice.line_ids.remove_move_reconcile()
        self.assertEqual(self.invoice.amount_residual, 100)

        payments_before = self.env['account.payment'].search([])
        with patch(MAYA_REQUEST, return_value={'status': 'PAYMENT_SUCCESS'}):
            self.invoice.action_l10n_ph_qrph_update_payment_status()
        self.assertEqual(self.env['account.payment'].search([]), payments_before)
        self.assertEqual(self.invoice.amount_residual, 100)
        self.assertFalse(self.invoice.l10n_ph_qrph_transaction_ids.settled_date)

    def test_paid_codes_are_registered_per_company(self):
        """ The cron looks at every company at once, while a payment cannot cover several. """
        other_data = self.setup_other_company(name='QRPH Other Company')
        other_company = other_data['company']
        other_company.qr_code = True
        # Only the company of the test class gets the account payments go through: without it, a
        # payment has no journal items to reconcile the invoice with once accounting is installed.
        in_outstanding_account = self.env['account.chart.template'].with_company(other_company).ref(
            'account_journal_payment_debit_account_id',
        )
        bank_journal = other_data['default_journal_bank']
        bank_journal.inbound_payment_method_line_ids[:1].payment_account_id = in_outstanding_account
        other_bank = self.env['res.partner.bank'].create({
            'account_number': '0987654321',
            'partner_id': other_company.partner_id.id,
            'company_id': other_company.id,
            'country_id': self.env.ref('base.ph').id,
            'l10n_ph_qrph_public_key': 'pk-other-key',
            'allow_out_payment': True,
        })
        other_invoice = self.env['account.move'].with_company(other_company).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'partner_bank_id': other_bank.id,
            'invoice_date': '2026-09-16',
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 50})],
            'qr_code_method': const.QR_METHOD,
        })
        other_invoice.action_post()
        invoices = self.invoice | other_invoice
        with patch(MAYA_REQUEST, side_effect=[self.maya_code, self.maya_second_code]):
            for invoice in invoices:
                invoice.with_context(is_online_qr=True)._generate_qr_code()

        self.env.ref('base.user_root').company_ids |= other_company
        # The cron logs what it could not pay and goes on, so a failure has to be read from the log.
        with (
            patch(MAYA_REQUEST, return_value={'status': 'PAYMENT_SUCCESS'}),
            self.assertNoLogs('odoo.addons.l10n_ph_qrph_maya.models.account_move', 'WARNING'),
        ):
            self._run_cron()

        self.assertEqual(invoices.mapped('amount_residual'), [0, 0])
        self.assertEqual(self.invoice.matched_payment_ids.company_id, self.invoice.company_id)
        self.assertEqual(other_invoice.matched_payment_ids.company_id, other_company)

    def test_paid_codes_are_registered_per_bank_account(self):
        """ The payment goes to the journal of the bank account the customer paid. """
        company = self.invoice.company_id
        other_bank = self.env['res.partner.bank'].create({
            'account_number': '1122334455',
            'partner_id': company.partner_id.id,
            'company_id': company.id,
            'country_id': self.env.ref('base.ph').id,
            'l10n_ph_qrph_public_key': 'pk-other-key',
            'allow_out_payment': True,
        })
        journals = self.env['account.journal'].create([{
            'name': f"Maya {bank.account_number}",
            'type': 'bank',
            'code': f'MY{index}',
            'company_id': company.id,
            'bank_account_id': bank.id,
        } for index, bank in enumerate(self.bank_qrph | other_bank)])
        other_invoice = self.invoice.copy({'partner_bank_id': other_bank.id, 'invoice_date': '2026-09-16'})
        other_invoice.action_post()
        invoices = self.invoice | other_invoice
        with patch(MAYA_REQUEST, side_effect=[self.maya_code, self.maya_second_code]):
            for invoice in invoices:
                invoice.with_context(is_online_qr=True)._generate_qr_code()

        with patch(MAYA_REQUEST, return_value={'status': 'PAYMENT_SUCCESS'}):
            invoices.action_l10n_ph_qrph_update_payment_status()

        self.assertEqual(self.invoice.matched_payment_ids.journal_id, journals[0])
        self.assertEqual(other_invoice.matched_payment_ids.journal_id, journals[1])

    def test_a_portal_customer_can_ask_maya_for_a_transaction(self):
        """ The customer looking at an invoice is not allowed to read the Maya settings of the account. """
        portal_user = new_test_user(self.env, login='qrph_portal', groups='base.group_portal')
        endpoint = 'payments/v1/qr/payments'
        with patch('requests.request') as request:
            request.return_value.json.return_value = self.maya_code
            response = self.bank_qrph.with_user(portal_user)._l10n_ph_qrph_make_request(
                endpoint, {'totalAmount': {'value': '100.00'}},
            )
        self.assertEqual(response, self.maya_code)
        self.assertIn(endpoint, request.call_args.args[1])

    @mute_logger('odoo.addons.l10n_ph_qrph_maya.models.account_move')
    def test_cron_goes_on_when_maya_fails_for_an_invoice(self):
        """ One invoice Maya cannot be asked about must not keep the others from being paid. """
        other_invoice = self.invoice.copy({'invoice_date': '2026-09-16'})
        other_invoice.action_post()
        with patch(MAYA_REQUEST, side_effect=[self.maya_code, self.maya_second_code]):
            for invoice in self.invoice | other_invoice:
                invoice.with_context(is_online_qr=True)._generate_qr_code()

        def request(endpoint, payload=None):
            if self.maya_code['paymentId'] in endpoint:
                raise MayaRequestError("Maya is down for this one")
            return {'status': 'PAYMENT_SUCCESS'}

        with patch(MAYA_REQUEST, side_effect=request):
            self._run_cron()
        self.assertEqual(self.invoice.amount_residual, 100)
        self.assertEqual(other_invoice.amount_residual, 0)

        with patch(MAYA_REQUEST, side_effect=request), self.assertRaises(MayaRequestError):
            self.invoice.action_l10n_ph_qrph_update_payment_status()

    def test_payment_is_for_what_the_customer_paid(self):
        """ The code was minted before part of the invoice was paid some other way: the customer paid the lot. """
        with patch(MAYA_REQUEST, return_value=self.maya_code):
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=self.invoice.ids,
        ).create({'amount': 40})._create_payments()
        self.assertEqual(self.invoice.amount_residual, 60)

        with patch(MAYA_REQUEST, return_value={'status': 'PAYMENT_SUCCESS'}):
            action = self.invoice.action_l10n_ph_qrph_update_payment_status()

        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertEqual(payment.amount, 100)
        self.assertEqual(self.invoice.payment_state, self.invoice._get_invoice_in_payment_state())

    def test_only_posted_invoices_are_checked(self):
        """ A cancelled invoice must neither be asked about to Maya nor paid, by the cron or by the action. """
        with patch(MAYA_REQUEST, return_value=self.maya_code):
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()
        self.invoice.button_draft()
        self.invoice.button_cancel()
        self.assertEqual(self.invoice.state, 'cancel')

        with patch(MAYA_REQUEST, return_value={'status': 'PAYMENT_SUCCESS'}) as request:
            self._run_cron()
            self.invoice.action_l10n_ph_qrph_update_payment_status()
        request.assert_not_called()
        self.assertFalse(self.invoice.matched_payment_ids)

    @mute_logger('odoo.addons.l10n_ph_qrph_maya.models.account_move')
    def test_cron_goes_on_when_a_payment_cannot_be_registered(self):
        with patch(MAYA_REQUEST, return_value=self.maya_code):
            self.invoice.with_context(is_online_qr=True)._generate_qr_code()
        transaction = self.invoice.l10n_ph_qrph_transaction_ids
        wizard_create_payments = (
            'odoo.addons.account.wizard.account_payment_register.AccountPaymentRegister._create_payments'
        )

        with patch(MAYA_REQUEST, return_value={'status': 'PAYMENT_SUCCESS'}), \
                patch(wizard_create_payments, side_effect=UserError("No way")):
            self._run_cron()
            self.assertEqual(self.invoice.amount_residual, 100)
            self.assertFalse(transaction.settled_date)
            self.assertFalse(
                any('Paid with QRPH' in (message.body or '') for message in self.invoice.message_ids),
                "the log of a payment that was not registered is rolled back",
            )

            with self.assertRaises(UserError):
                self.invoice.action_l10n_ph_qrph_update_payment_status()

    def test_code_needs_pesos_and_a_key(self):
        error = self.bank_qrph._get_error_messages_for_qr(const.QR_METHOD, self.partner_a, self.env.ref('base.USD'))
        self.assertIn("currency other than PHP", error)

        self.bank_qrph.l10n_ph_qrph_public_key = False
        error = self.bank_qrph._get_error_messages_for_qr(const.QR_METHOD, self.partner_a, self.env.ref('base.PHP'))
        self.assertIn("public key", error)

    def test_code_needs_an_amount(self):
        """ There is no amount-less QRPH code, which is what the point of sale asks for when offline. """
        with self.assertRaises(UserError):
            self.bank_qrph.build_qr_code_value(
                0, 'a reference', '', self.env.ref('base.PHP'), self.partner_a, const.QR_METHOD, silent_errors=False,
            )

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
        # The cron goes on when an invoice fails, so reaching Maya has to be read from the call itself.
        with patch(MAYA_REQUEST) as request:
            self._run_cron()
        request.assert_not_called()
        self.assertEqual(self.env['account.payment'].search([]), payments_before)

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
        self.assertEqual(
            len(self.invoice.message_ids.filtered(lambda message: 'short of the' in (message.body or ''))),
            1,
            "the merchant is told on the invoice",
        )

        with patch(MAYA_REQUEST, return_value={'status': 'PAYMENT_SUCCESS'}):
            self.assertFalse(transaction._get_paid_transaction(140))
        self.assertEqual(
            len(self.invoice.message_ids.filtered(lambda message: 'short of the' in (message.body or ''))),
            1,
            "and only once",
        )

        self.assertEqual(transaction._get_paid_transaction(100), transaction, "it does settle what it was minted for")
        self.assertEqual(transaction._get_paid_transaction(60), transaction, "and anything it covers")
