# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.fields import Command
from odoo.tests import new_test_user, tagged
from odoo.tools import format_amount

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ph_qrph_maya import const
from odoo.addons.point_of_sale.tests.common import TestPoSCommon

MAYA_REQUEST = 'odoo.addons.l10n_ph_qrph_maya.models.res_bank.ResPartnerBank._l10n_ph_qrph_make_request'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPhKioskQrph(TestPoSCommon):
    """ A kiosk customer is alone with the screen, so nothing they do to it may settle their order.

    Maya has no way of taking a code back once it is out, which is what these tests are about: a
    code the kiosk gave up on stays payable for as long as Maya honours it, and what it was minted
    for is not necessarily what the order ended up costing.
    """

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
        cls.config.write({
            'self_ordering_mode': 'kiosk',
            'payment_method_ids': [Command.link(cls.qrph_method.id)],
        })

        # The kiosk acts as the default user of its configuration, who may read the transactions of
        # an order but not write them.
        cls.kiosk_user = new_test_user(
            cls.env, login='qrph_kiosk', groups='point_of_sale.group_pos_user',
            company_id=company.id, company_ids=[Command.set(company.ids)],
        )
        cls.config.self_ordering_default_user_id = cls.kiosk_user
        cls.kiosk_method = cls.qrph_method.with_user(cls.kiosk_user)

        cls.snack = cls.create_product("Snack", cls.categ_basic, 10.0)
        cls.meal = cls.create_product("Meal", cls.categ_basic, 90.0)

    def setUp(self):
        super().setUp()
        self.open_new_session()

    def test_a_code_minted_for_less_does_not_buy_the_order_it_grew_into(self):
        """ The customer is handed a code, goes back to their order, adds to it, and pays the code.

        That code is payable — Maya cannot take it back — but it no longer buys this order, so
        settling on it would hand over the difference.
        """
        order = self._create_kiosk_order(self.snack)
        self.assertEqual(order.amount_total, 10)
        cheap_code = self._mint(order, 10, 'maya-cheap-code')

        self._add_to_order(order, self.meal)
        self.assertEqual(order.amount_total, 100)
        self._mint(order, 100, 'maya-real-code')

        with self._maya_reports_paid('maya-cheap-code'), self._spy_on_payment_result() as payment_result:
            self.assertFalse(self.kiosk_method._l10n_ph_kiosk_qrph_settle_if_paid(order))

        payment_result.assert_not_called()
        self.assertEqual(order.state, 'draft', "the order is not bought by a code minted for a tenth of it")
        self.assertFalse(order.payment_ids)
        # The money did reach Maya, so the merchant has to be able to see it and refund it.
        self.assertEqual(cheap_code.state, 'paid')
        self.assertFalse(cheap_code.settled_date)
        self.assertTrue(
            any('short of the' in (message.body or '') for message in order.message_ids),
            "the merchant is told on the order",
        )

        # The kiosk is told as well, otherwise the customer who paid is only ever told that nothing
        # was received.
        with self._maya_reports_paid('maya-cheap-code'):
            result = self.kiosk_method.l10n_ph_kiosk_qrph_verify_payment(order.uuid)
        self.assertFalse(result['paid'])
        self.assertEqual(result['short_payment']['received'], format_amount(self.env, 10, order.currency_id))
        self.assertEqual(result['short_payment']['total'], format_amount(self.env, 100, order.currency_id))

    def test_a_code_covering_the_order_settles_it_once(self):
        """ The code the customer was actually shown pays the order, and pays it only once. """
        order = self._create_kiosk_order(self.meal)
        code = self._mint(order, order.amount_total, 'maya-real-code')

        with self._maya_reports_paid('maya-real-code'), self._spy_on_payment_result() as payment_result:
            self.assertTrue(self.kiosk_method._l10n_ph_kiosk_qrph_settle_if_paid(order))

        payment_result.assert_called_once_with('Success')
        self.assertEqual(order.state, 'paid')
        self.assertEqual(sum(order.payment_ids.mapped('amount')), 90)
        self.assertTrue(code.settled_date)

        # The customer may ask about their payment again: the kiosk still gets a yes, the order
        # still has one payment.
        payments = order.payment_ids
        with self._maya_reports_paid('maya-real-code'), self._spy_on_payment_result() as payment_result:
            self.assertTrue(self.kiosk_method._l10n_ph_kiosk_qrph_settle_if_paid(order))
        payment_result.assert_not_called()
        self.assertEqual(order.payment_ids, payments)

    def _create_kiosk_order(self, product, **vals):
        """ Return a draft kiosk order, which is what the kiosk stores before showing a code. """
        order = self.env['pos.order'].create({
            **vals,
            'company_id': self.config.company_id.id,
            'session_id': self.pos_session.id,
            'amount_total': 0,
            'amount_paid': 0,
            'amount_tax': 0,
            'amount_return': 0,
            'lines': [self._line_vals(product)],
        })
        self._recompute_order(order)
        return order

    def _add_to_order(self, order, product):
        order.write({'lines': [self._line_vals(product)]})
        self._recompute_order(order)

    def _line_vals(self, product):
        return Command.create({
            'product_id': product.id,
            'qty': 1,
            'price_unit': product.lst_price,
            'price_subtotal': product.lst_price,
            'price_subtotal_incl': product.lst_price,
            'tax_ids': False,
        })

    def _recompute_order(self, order):
        order.lines._onchange_amount_line_all()
        order._compute_prices()

    def _mint(self, order, amount, maya_payment_id):
        """ Stand in for a code Maya handed out for an order, at the amount it was minted for. """
        Transaction = self.env['l10n_ph.qrph.transaction']
        return Transaction.create({
            **Transaction._get_record_vals('pos.order', order.id, order.uuid),
            'bank_id': self.bank_qrph.id,
            'currency_id': order.currency_id.id,
            'amount': amount,
            'maya_payment_id': maya_payment_id,
            'qr_code_body': f'payload-for-{maya_payment_id}',
        })

    def _spy_on_payment_result(self):
        """ Watch what the kiosk is told about the payment, which the bus would carry. """
        return patch.object(self.env.registry['pos.order'], '_send_payment_result', autospec=False)

    def _maya_reports_paid(self, maya_payment_id):
        """ Have Maya report one code paid and every other one still waiting to be scanned. """
        def request(endpoint, payload=None):
            return {'status': 'PAYMENT_SUCCESS' if maya_payment_id in endpoint else 'PENDING_PAYMENT'}

        return patch(MAYA_REQUEST, side_effect=request)
