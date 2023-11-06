# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
import threading

from odoo import tools, Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.pos_online_payment.models.pos_order import PosOrder
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

        real_get_and_set_online_payments_data = PosOrder.get_and_set_online_payments_data

        def _fake_get_and_set_online_payments_data(method_self, next_online_payment_amount=False):
            pos_order_id = method_self.id
            order_access_token = method_self.access_token
            expected_payment_provider_id = self.payment_provider.id
            if not isinstance(next_online_payment_amount, bool) and not tools.float_is_zero(next_online_payment_amount, precision_rounding=method_self.currency_id.rounding) and next_online_payment_amount > 0:
                # Delay must be long enough to execute _fake_online_payment after the current RPC call is answered
                t = threading.Timer(5, self._fake_online_payment, args=(pos_order_id, order_access_token, expected_payment_provider_id))
                t.start()

            return real_get_and_set_online_payments_data(method_self, next_online_payment_amount)

        self._fake_get_and_set_online_payments_data = _fake_get_and_set_online_payments_data

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
        params = self.pos_config.current_session_id._loader_params_product_product()
        self.assertTrue(params)
        pos_config_products_domain = params['search_params']['domain']
        self.assertTrue(pos_config_products_domain)
        tests_products_domain = AND([pos_config_products_domain, ['&', '&', ('name', '=', 'Letter Tray'), ('list_price', '=', 4.8), ('available_in_pos', '=', True)]])
        # active_test=False to follow pos.config:get_pos_ui_product_product_by_params
        self.assertEqual(self.env['product.product'].with_context(active_test=False).search_count(tests_products_domain, limit=1), 1)

    def _start_tour(self, tour_name):
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, tour_name, login="pos_op_user")

    def test_server_fake_payment_tour(self):
        self._open_session_ui()

        before_tour_datetime = fields.Datetime.now()
        with patch.object(PosOrder, 'get_and_set_online_payments_data', self._fake_get_and_set_online_payments_data):
            self._start_tour('OnlinePaymentServerFakePaymentTour')

        test_orders = self.env['pos.order'].search(['&', ('config_id', '=', self.pos_config.id), ('date_order', '>=', before_tour_datetime)])
        self.assertEqual(len(test_orders), 1)
        for order in test_orders:
            self.assertEqual(order.state, 'done', "Validated order has payment of " + str(order.amount_paid) + " and total of " + str(order.amount_total))

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
