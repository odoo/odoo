# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid
from unittest.mock import patch

from odoo import Command, fields
from odoo.tools import mute_logger
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.pos_online_payment.tests.online_payment_common import OnlinePaymentCommon
from odoo.addons.account.models.account_payment_method import AccountPaymentMethod
from odoo.osv.expression import AND
from odoo.addons.point_of_sale.tests.common import archive_products

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(AccountTestInvoicingCommon, OnlinePaymentCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Code from addons/account_payment/tests/common.py:
        Method_get_payment_method_information = AccountPaymentMethod._get_payment_method_information

        def _get_payment_method_information(self):
            res = Method_get_payment_method_information(self)
            res['none'] = {'mode': 'multi', 'domain': [('type', '=', 'bank')]}
            return res

        with patch.object(AccountPaymentMethod, '_get_payment_method_information', _get_payment_method_information):
            cls.env['account.payment.method'].sudo().create({
                'name': 'Dummy method',
                'code': 'none',
                'payment_type': 'inbound'
            })
        # End of code from addons/account_payment/tests/common.py

        # Code inspired by addons/point_of_sale/tests/common.py:
        cls.company = cls.company_data['company']
        cls.cash_journal = cls.env['account.journal'].create({
            'name': 'Cash Journal for POS OP Test',
            'type': 'cash',
            'company_id': cls.company.id,
            'code': 'POPCH',
            'sequence': 10,
        })

        cls.old_account_default_pos_receivable_account_id = cls.company.account_default_pos_receivable_account_id
        cls.account_default_pos_receivable_account_id = cls.env['account.account'].create({
            'code': 'X1012.POSOP',
            'name': 'Debtors - (POSOP)',
            'account_type': 'asset_receivable',
            'reconcile': True,
        })
        cls.company.account_default_pos_receivable_account_id = cls.account_default_pos_receivable_account_id
        cls.receivable_cash_account = cls.copy_account(cls.company.account_default_pos_receivable_account_id, {'name': 'POS OP Test Receivable Cash'})

        cls.cash_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Cash',
            'journal_id': cls.cash_journal.id,
            'receivable_account_id': cls.receivable_cash_account.id,
            'company_id': cls.company.id,
        })
        # End of code inspired by addons/point_of_sale/tests/common.py

        cls.payment_provider = cls.provider # The dummy_provider used by the tests of the 'payment' module.

        cls.payment_provider_old_company_id = cls.payment_provider.company_id.id
        cls.payment_provider_old_journal_id = cls.payment_provider.journal_id.id
        cls.payment_provider.write({
            'company_id': cls.company.id,
            'journal_id': cls.company_data['default_journal_bank'].id,
        })

        cls.online_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Online payment',
            'is_online_payment': True,
            'online_payment_provider_ids': [Command.set([cls.payment_provider.id])],
        })

        cls.sales_journal = cls.env['account.journal'].create({
            'name': 'Sales Journal for POS OP Test',
            'code': 'POPSJ',
            'type': 'sale',
            'company_id': cls.company.id
        })

        cls.pos_config = cls.env['pos.config'].create({
            'name': 'POS OP Test Shop',
            'module_pos_restaurant': False,
            'invoice_journal_id': cls.sales_journal.id,
            'journal_id': cls.sales_journal.id,
            'payment_method_ids': [Command.link(cls.cash_payment_method.id), Command.link(cls.online_payment_method.id)],
        })

        # Code from addons/point_of_sale/tests/test_frontend.py:
        cls.pos_user = cls.env['res.users'].create({
            'name': 'A simple PoS man!',
            'login': 'pos_op_user',
            'password': 'pos_op_user',
            'groups_id': [
                (4, cls.env.ref('base.group_user').id),
                (4, cls.env.ref('point_of_sale.group_pos_user').id),
            ],
        })
        cls.pos_user.partner_id.email = 'pos_op_user@test.com'
        # End of code from addons/point_of_sale/tests/test_frontend.py

        archive_products(cls.env)

        pos_categ_misc = cls.env['pos.category'].create({
            'name': 'Miscellaneous',
        })
        cls.letter_tray = cls.env['product.product'].create({
            'name': 'Letter Tray',
            'type': 'product',
            'available_in_pos': True,
            'list_price': 4.8,
            'taxes_id': False,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
        })

    # Code from addons/account_payment/tests/common.py
    @classmethod
    def _prepare_provider(cls, provider_code='none', company=None, update_values=None):
        """ Override of `payment` to prepare and return the first provider matching the given
        provider and company.

        If no provider is found in the given company, we duplicate the one from the base company.
        All other providers belonging to the same company are disabled to avoid any interferences.

        :param str provider_code: The code of the provider to prepare.
        :param recordset company: The company of the provider to prepare, as a `res.company` record.
        :param dict update_values: The values used to update the provider.
        :return: The provider to prepare, if found.
        :rtype: recordset of `payment.provider`
        """
        provider = super()._prepare_provider(provider_code, company, update_values)
        if not provider.journal_id:
            provider.journal_id = cls.env['account.journal'].search(
                [('company_id', '=', provider.company_id.id), ('type', '=', 'bank')],
                limit=1,
            )
        return provider
    # End of code from addons/account_payment/tests/common.py

    def setUp(self):
        self.enable_reconcile_after_done_patcher = False

        super(TestUi, self).setUp()

        self.assertTrue(self.company)
        self.assertTrue(self.cash_journal)
        self.assertTrue(self.account_default_pos_receivable_account_id)
        self.assertTrue(self.receivable_cash_account)
        self.assertTrue(self.sales_journal)
        self.assertTrue(self.cash_payment_method)
        self.assertTrue(self.payment_provider)
        self.assertTrue(self.online_payment_method)
        self.assertTrue(self.pos_config)
        self.assertTrue(self.pos_user)

    def _open_session_ui(self):
        self.pos_config.with_user(self.pos_user).open_ui()

        # Checks that the products used in the tours are available in this pos_config.
        # This code is executed here because _loader_params_product_product is defined in pos.session
        # and not in pos.config.
        pos_config_products_domain = self.pos_config._get_available_product_domain()
        self.assertTrue(pos_config_products_domain)
        tests_products_domain = AND([pos_config_products_domain, ['&', '&', ('name', '=', 'Letter Tray'), ('list_price', '=', 4.8), ('available_in_pos', '=', True)]])
        # active_test=False to follow pos.config:get_pos_ui_product_product_by_params
        self.assertEqual(self.env['product.product'].with_context(active_test=False).search_count(tests_products_domain, limit=1), 1)

    def _start_tour(self, tour_name):
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, tour_name, login="pos_op_user")

    def _open_session_fake_cashier_unpaid_order(self):
        self._open_session_ui()

        current_session = self.pos_config.current_session_id
        current_session.set_cashbox_pos(0, None)

        # Simulate a cashier saving an unpaid order on the server
        product = self.letter_tray
        order_uid = '00055-001-0001'
        order_pos_reference = 'Order ' + order_uid

        untax, atax = self.compute_tax(product, product.list_price)
        order_data = {
            'data': {
                'uid': order_uid,
                'name': order_pos_reference,
                'pos_session_id': current_session.id,
                'sequence_number': 1,
                'user_id': self.pos_user.id,
                'partner_id': False,
                'access_token': str(uuid.uuid4()),
                'amount_paid': 0,
                'amount_return': 0,
                'amount_tax': atax,
                'amount_total': untax + atax,
                'date_order': fields.Datetime.to_string(fields.Datetime.now()),
                'fiscal_position_id': False,
                'lines': [[0, 0, {
                    'product_id': product.id,
                    'qty': 1,
                    'discount': 0,
                    'tax_ids': [(6, 0, product.taxes_id.ids)],
                    'price_unit': product.list_price,
                    'price_subtotal': untax,
                    'price_subtotal_incl': untax + atax,
                    'pack_lot_ids': [],
                }]],
                'statement_ids': [],
            },
            'to_invoice': False,
        }

        create_result = self.env['pos.order'].with_user(self.pos_user).create_from_ui([order_data], draft=True)
        self.assertEqual(len(current_session.order_ids), 1)
        order_id = next(result_order_data for result_order_data in create_result if result_order_data['pos_reference'] == order_pos_reference)['id']

        order = self.env['pos.order'].search([('id', '=', order_id)])
        self.assertEqual(order.state, 'draft')
        return order

    def _test_fake_customer_online_payment(self, payments_amount=1, cashier_request_for_remaining=True):
        order = self._open_session_fake_cashier_unpaid_order()
        current_session = self.pos_config.current_session_id

        amount_per_payment = order.amount_total / payments_amount
        for i in range(payments_amount):
            if i != payments_amount - 1 or cashier_request_for_remaining:
                # Simulate the cashier requesting an online payment for the order
                op_data = order.with_user(self.pos_user).get_and_set_online_payments_data(amount_per_payment)
                self.assertEqual(op_data['id'], order.id)
                self.assertTrue('paid_order' not in op_data)

            # Simulate the customer paying the order online
            self._fake_online_payment(order.id, order.access_token, self.payment_provider.id)

        self.assertEqual(order.state, 'paid')
        op_data = order.with_user(self.pos_user).get_and_set_online_payments_data()
        self.assertEqual(op_data['id'], order.id)
        self.assertTrue('paid_order' in op_data)

        # Simulate the cashier closing the session (to detect eventual accounting issues)
        total_cash_payment = sum(current_session.order_ids.filtered(lambda o: o.state != 'cancel').payment_ids.filtered(lambda payment: payment.payment_method_id.type == 'cash').mapped('amount'))
        current_session.post_closing_cash_details(total_cash_payment)
        close_result = current_session.close_session_from_ui()

        self.assertTrue(close_result['successful'])
        self.assertEqual(current_session.state, 'closed', 'Session was not properly closed')

        self.assertEqual(order.state, 'done', "Validated order has payment of " + str(order.amount_paid) + " and total of " + str(order.amount_total))

    # Code from addons/point_of_sale/tests/test_point_of_sale_flow.py
    def compute_tax(self, product, price, qty=1, taxes=None):
        if not taxes:
            taxes = product.taxes_id.filtered(lambda t: t.company_id.id == self.env.company.id)
        currency = self.pos_config.currency_id
        res = taxes.compute_all(price, currency, qty, product=product)
        untax = res['total_excluded']
        return untax, sum(tax.get('amount', 0.0) for tax in res['taxes'])
    # End of code from addons/point_of_sale/tests/test_point_of_sale_flow.py

    def test_1_online_payment_with_cashier(self):
        self._test_fake_customer_online_payment(payments_amount=1, cashier_request_for_remaining=True)

    def test_1_online_payment_without_cashier(self):
        self._test_fake_customer_online_payment(payments_amount=1, cashier_request_for_remaining=False)

    def test_2_online_payments_with_cashier(self):
        self._test_fake_customer_online_payment(payments_amount=2, cashier_request_for_remaining=True)

    def test_invalid_access_token(self):
        order = self._open_session_fake_cashier_unpaid_order()

        with mute_logger('odoo.http'): # Mutes "The provided order or access token is invalid." online payment portal error.
            self.assertRaises(AssertionError, self._fake_open_pos_order_pay_page, order.id, order.access_token[:-1])
            self.assertRaises(AssertionError, self._fake_open_pos_order_pay_page, order.id, '')

            self.assertRaises(AssertionError, self._fake_open_pos_order_pay_confirmation_page, order.id, order.access_token[:-1], 1)
            self.assertRaises(AssertionError, self._fake_open_pos_order_pay_confirmation_page, order.id, '', 1)

        self.assertEqual(order.state, 'draft')

    def test_local_fake_paid_data_tour(self):
        self._open_session_ui()
        self._start_tour('OnlinePaymentLocalFakePaidDataTour')

    def test_errors_tour(self):
        self._open_session_ui()
        self._start_tour('OnlinePaymentErrorsTour')

    @classmethod
    def tearDownClass(cls):
        # Restore company values after the tests
        cls.company.account_default_pos_receivable_account_id = cls.old_account_default_pos_receivable_account_id

        # Restore dummy_provider values after the tests
        cls.payment_provider.company_id = cls.payment_provider_old_company_id
        cls.payment_provider.journal_id = cls.payment_provider_old_journal_id

        # The online payment method cannot be deleted because it is used by a payment in the database.
        # It would require to delete the paid orders of the tests, the corresponding accounting, the session data...
        cls.pos_config.payment_method_ids = [Command.unlink(cls.online_payment_method.id)]
        cls.cash_payment_method.unlink()
        cls.receivable_cash_account.unlink()
        cls.cash_journal.unlink()
        cls.account_default_pos_receivable_account_id.unlink()
