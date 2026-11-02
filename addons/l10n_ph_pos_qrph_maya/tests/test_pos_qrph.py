# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ph_qrph_maya import const
from odoo.addons.point_of_sale.tests.common import TestPoSCommon

MAYA_REQUEST = 'odoo.addons.l10n_ph_qrph_maya.models.res_bank.ResPartnerBank._l10n_ph_qrph_make_request'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPhPosQrph(TestPoSCommon):
    """ A cashier is shown a QRPH transaction for an order that is not stored until it is paid. """

    @classmethod
    @AccountTestInvoicingCommon.setup_country('ph')
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
        cls.qrph_journal = cls.env['account.journal'].create({
            'name': "QRPH Bank",
            'type': 'bank',
            'code': 'QRPHB',
            'company_id': company.id,
            'bank_account_id': cls.bank_qrph.id,
        })
        cls.qrph_method = cls.env['pos.payment.method'].create({
            'name': "QRPH",
            'company_id': company.id,
            'type': 'bank',
            'journal_id': cls.qrph_journal.id,
            'payment_method_type': 'bank_qr_code',
            'qr_code_method': const.QR_METHOD,
        })

        cls.config = cls.basic_config
        cls.config.write({'payment_method_ids': [Command.link(cls.qrph_method.id)]})
        cls.meal = cls.create_product("Meal", cls.categ_basic, 90.0)
        cls.cashier = new_test_user(
            cls.env, login='qrph_cashier', groups='point_of_sale.group_pos_user',
            company_id=company.id, company_ids=[Command.set(company.ids)],
        )

    def setUp(self):
        super().setUp()
        self.open_new_session()

    def test_a_transaction_minted_before_the_order_is_stored_is_linked_to_it_afterwards(self):
        order_uuid = str(uuid.uuid4())
        transaction = self._mint(order_uuid, 90)
        self.assertFalse(transaction.res_id, "there is no order to link yet")
        Transaction = self.env['l10n_ph.qrph.transaction']
        self.assertEqual(
            Transaction._get_latest_transaction('pos.order', None, self.env.company.id, order_uuid),
            transaction,
        )

        order = self._process_order(order_uuid)

        self.assertEqual(transaction.res_id, order.id)
        self.assertEqual(order.l10n_ph_qrph_transaction_ids, transaction)
        self.assertEqual(transaction._get_record(), order)

    def test_a_paid_order_settles_the_transaction_that_paid_it(self):
        """ Once the order is stored as paid, the transaction behind its payment cannot pay again. """
        order_uuid = str(uuid.uuid4())
        paid = self._mint(order_uuid, 90, state='paid')

        order = self._process_order(order_uuid)
        self.assertFalse(paid.settled_date, "an order still being keyed in has not recorded the payment")

        self._pay_order(order, 90)

        self.assertEqual(order.state, 'paid')
        self.assertTrue(paid.settled_date)

    def test_a_paid_order_leaves_a_short_transaction_unsettled(self):
        order_uuid = str(uuid.uuid4())
        short = self._mint(order_uuid, 50, state='paid')

        order = self._process_order(order_uuid)
        self._pay_order(order, 90)

        self.assertEqual(order.state, 'paid')
        self.assertFalse(short.settled_date, "the merchant still has to settle the difference")

    def test_a_pos_user_only_sees_the_transactions_of_pos_orders(self):
        Transaction = self.env['l10n_ph.qrph.transaction']
        order_transaction = self._mint(str(uuid.uuid4()), 90)
        Transaction.create({
            **Transaction._get_record_vals('account.move', '1'),
            'bank_id': self.bank_qrph.id,
            'currency_id': self.config.currency_id.id,
            'amount': 90,
            'maya_payment_id': 'maya-invoice-payment',
            'qr_code_body': 'payload-for-maya-invoice-payment',
        })

        self.assertEqual(Transaction.with_user(self.cashier).search([]), order_transaction)

    def test_a_pos_user_cannot_make_a_transaction_paid(self):
        """ Only what Maya answers makes a transaction paid: a cashier must not be able to say it. """
        Transaction = self.env['l10n_ph.qrph.transaction']
        pending = self._mint(str(uuid.uuid4()), 90)

        with self.assertRaises(AccessError):
            pending.with_user(self.cashier).write({'state': 'paid'})
        with self.assertRaises(AccessError):
            Transaction.with_user(self.cashier).create({
                **Transaction._get_record_vals('pos.order', None, str(uuid.uuid4())),
                'bank_id': self.bank_qrph.id,
                'currency_id': self.config.currency_id.id,
                'amount': 90,
                'state': 'paid',
                'maya_payment_id': 'maya-made-up',
                'qr_code_body': 'payload-for-maya-made-up',
            })

    def test_a_cashier_mints_a_transaction_for_their_order(self):
        order_uuid = str(uuid.uuid4())
        bank = self.bank_qrph.with_user(self.cashier).with_context(
            l10n_ph_qrph_model='pos.order',
            l10n_ph_qrph_model_uuid=order_uuid,
            l10n_ph_qrph_company_id=self.config.company_id.id,
        )
        with patch('requests.request') as request:
            request.return_value.json.return_value = {'paymentId': 'maya-minted', 'qrCodeBody': 'payload-minted'}
            qr_content = bank._get_qr_vals(const.QR_METHOD, 90, self.config.currency_id, self.env['res.partner'], 'Order', '')

        self.assertEqual(qr_content, 'payload-minted')
        transaction = self.env['l10n_ph.qrph.transaction'].search([('pos_order_uuid', '=', order_uuid)])
        self.assertEqual(transaction.maya_payment_id, 'maya-minted')
        self.assertEqual(transaction.company_id, self.config.company_id)

    def test_verifying_something_that_is_not_a_qrph_payment_is_always_fine(self):
        self.assertTrue(self.cash_pm1.with_user(self.cashier).l10n_ph_qrph_verify_payment_status(
            str(uuid.uuid4()), self.config.company_id.id, 90,
        ))

    def test_verifying_needs_an_amount_and_a_transaction(self):
        method = self.qrph_method.with_user(self.cashier)
        order_uuid = str(uuid.uuid4())
        company_id = self.config.company_id.id

        with self.assertRaises(UserError):
            method.l10n_ph_qrph_verify_payment_status(order_uuid, company_id, None)
        with self.assertRaises(UserError):
            method.l10n_ph_qrph_verify_payment_status(order_uuid, company_id, 90)

        self._mint(order_uuid, 90)
        with self.assertRaises(UserError):
            method.l10n_ph_qrph_verify_payment_status(order_uuid, company_id + 1000, 90)

    @mute_logger('odoo.addons.l10n_ph_qrph_maya.models.l10n_ph_qrph_transaction')
    def test_verifying_follows_what_maya_reports(self):
        method = self.qrph_method.with_user(self.cashier)
        order_uuid = str(uuid.uuid4())
        company_id = self.config.company_id.id
        transaction = self._mint(order_uuid, 90)

        with patch(MAYA_REQUEST, return_value={'status': 'PENDING_PAYMENT'}):
            self.assertFalse(method.l10n_ph_qrph_verify_payment_status(order_uuid, company_id, 90))
        with patch(MAYA_REQUEST, return_value={'status': 'PAYMENT_SUCCESS'}):
            self.assertFalse(
                method.l10n_ph_qrph_verify_payment_status(order_uuid, company_id, 140),
                "a transaction minted for 90 does not pay 140",
            )
            self.assertTrue(method.l10n_ph_qrph_verify_payment_status(order_uuid, company_id, 90))
        self.assertEqual(transaction.state, 'paid')
        self.assertFalse(transaction.settled_date, "only storing the paid order settles the transaction")

    def test_a_paid_code_does_not_vouch_for_the_next_payment_line(self):
        """ An order paid with two codes, 70 then 30: the 30 is not received because the 70 was. """
        method = self.qrph_method.with_user(self.cashier)
        order_uuid = str(uuid.uuid4())
        company_id = self.config.company_id.id
        first = self._mint(order_uuid, 70, state='paid')
        second = self._mint(order_uuid, 30)

        with patch(MAYA_REQUEST, return_value={'status': 'PENDING_PAYMENT'}):
            self.assertFalse(method.l10n_ph_qrph_verify_payment_status(order_uuid, company_id, 30))
        with patch(MAYA_REQUEST, return_value={'status': 'PAYMENT_SUCCESS'}):
            self.assertTrue(method.l10n_ph_qrph_verify_payment_status(order_uuid, company_id, 30))
        self.assertEqual((first | second).mapped('state'), ['paid', 'paid'])

    def _mint(self, order_uuid, amount, state='pending'):
        """ Stand in for a transaction Maya handed out for an order, at the amount it was minted for. """
        Transaction = self.env['l10n_ph.qrph.transaction']
        return Transaction.create({
            **Transaction._get_record_vals('pos.order', None, order_uuid),
            'bank_id': self.bank_qrph.id,
            'currency_id': self.config.currency_id.id,
            'amount': amount,
            'state': state,
            'maya_payment_id': f'maya-{order_uuid}-{amount}',
            'qr_code_body': f'payload-for-{order_uuid}-{amount}',
        })

    def _order_vals(self, order_uuid):
        return {
            'uuid': order_uuid,
            'company_id': self.config.company_id.id,
            'session_id': self.pos_session.id,
            'amount_total': 90,
            'amount_paid': 90,
            'amount_tax': 0,
            'amount_return': 0,
        }

    def _process_order(self, order_uuid):
        """ Store a draft order the way the point of sale does, with no more access than a cashier. """
        cashier_orders = self.env['pos.order'].with_user(self.cashier)
        return self.env['pos.order'].browse(cashier_orders._process_order({
            **self._order_vals(order_uuid),
            'state': 'draft',
            'lines': [Command.create({
                'product_id': self.meal.id,
                'qty': 1,
                'price_unit': 90,
                'price_subtotal': 90,
                'price_subtotal_incl': 90,
                'tax_ids': False,
            })],
        }, False))

    def _pay_order(self, order, amount):
        """ Store the order again, as the point of sale does once it is paid with QRPH. """
        vals = self._order_vals(order.uuid)
        self.env['pos.order'].with_user(self.cashier)._process_order({
            **vals,
            'state': 'paid',
            'payment_ids': [Command.create({
                'amount': amount,
                'payment_date': fields.Datetime.now(),
                'payment_method_id': self.qrph_method.id,
            })],
        }, order)
