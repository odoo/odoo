# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.exceptions import UserError, ValidationError


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSBasicConfig(TestPoSCommon):
    """ Test PoS with basic configuration

    The tests contain base scenarios in using pos.
    More specialized cases are tested in other tests.
    """
    _test_user_groups = None  # FIXME list needed groups

    def setUp(self):
        super(TestPoSBasicConfig, self).setUp()
        self.config = self.basic_config
        self.product0 = self.create_product('Product 0', self.categ_basic, 0.0, 0.0)
        self.product1 = self.create_product('Product 1', self.categ_basic, 10.0, 5)
        self.product2 = self.create_product('Product 2', self.categ_basic, 20.0, 10)
        self.product3 = self.create_product('Product 3', self.categ_basic, 30.0, 15)
        self.product4 = self.create_product('Product_4', self.categ_basic, 9.96, 4.98)
        self.product99 = self.create_product('Product_99', self.categ_basic, 99, 50)
        self.product_multi_tax = self.create_product('Multi-tax product', self.categ_basic, 100, 100, (self.taxes['tax8'] | self.taxes['tax9']).ids)
        self.company_data_2 = self.setup_other_company()

    def test_pos_session_name_sequencing(self):
        """ This test check if the session name is correctly set according to the sequence """

        sequence = self.env['ir.sequence'].search([('code', '=', 'pos.session')])
        sequence.prefix = '/'
        sequence.write({'number_next_actual': 1000})
        name = self.config.name

        self.open_new_session(0)
        self.assertEqual(self.pos_session.name, name + '/01000')

        self.pos_session.close_session_from_ui()

        sequence.prefix = 'TEST/'

        self.open_new_session(0)
        self.assertEqual(self.pos_session.name, 'TEST/01001')

    def test_load_data_should_not_fail(self):
        """load_data shouldn't fail

        (Include test conditions here if possible)

        - When there are partners that belong to different company
        """

        # create a partner that belongs to different company
        company2 = self.company_data_2['company']
        self.env['res.partner'].create({
            'name': 'Test',
            'company_id': company2.id,
        })

        self.open_new_session()

        # calling load_data should not raise an error
        self.pos_session.load_data([])

    def test_load_data_picks_the_company_website_domain(self):
        if self.env['ir.module.module']._get('website').state != 'installed':
            self.skipTest("website module is required for this test")

        company_website = self.config.company_id.website_id

        if company_website:
            company_website.write({'domain': 'https://custom.test.domain.com'})
            self.open_new_session()
            response = self.pos_session.load_data([])

            self.assertEqual(response['pos.config'][0]['_base_url'], company_website.domain)

    def test_invoice_past_refund(self):
        """ Test invoicing a past refund

        Orders
        ======
        +------------------+----------+-----------+----------+-----+-------+
        | order            | payments | invoiced? | product  | qty | total |
        +------------------+----------+-----------+----------+-----+-------+
        | order 1          | cash     | no        | product3 |   1 |    30 |
        +------------------+----------+-----------+----------+-----+-------+
        | order 2 (return) | cash     | no        | product3 |  -1 |   -30 |
        +------------------+----------+-----------+----------+-----+-------+

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | sale (sales)        |     -30 |
        | sale (refund)       |      30 |
        +---------------------+---------+
        | Total balance       |     0.0 |
        +---------------------+---------+
        """
        def _before_closing_cb():
            # Return the order
            order_to_return = self.pos_session.order_ids.filtered(lambda order: '12345-123-1234' in order.uuid)
            order_to_return.refund()
            refund_order = self.pos_session.order_ids.filtered(lambda order: order.state == 'draft')

            # Check if there's an amount to pay
            self.assertAlmostEqual(refund_order.amount_total - refund_order.amount_paid, -30)

            # Pay the refund
            context_make_payment = {"active_ids": [refund_order.id], "active_id": refund_order.id}
            make_payment = self.env['pos.make.payment'].with_context(context_make_payment).create({
                'payment_method_id': self.cash_pm1.id,
                'amount': -30,
            })
            make_payment.check()

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product3, 1)], 'payments': [(self.cash_pm1, 30)], 'uuid': '12345-123-1234'},
            ],
            'before_closing_cb': _before_closing_cb,
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 30, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 30, 'credit': 0, 'reconciled': False},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [],
            },
        })

        closed_session = self.pos_session
        self.assertTrue(closed_session.state == 'closed', 'Session should be closed.')

        return_to_invoice = closed_session.order_ids[1]
        test_customer = self.env['res.partner'].create({'name': 'Test Customer'})
        new_session_date = return_to_invoice.date_order + relativedelta(days=2)

        with freeze_time(new_session_date):
            # Create a new session after 2 days
            self.open_new_session(0)
            # Invoice the uninvoiced refund
            return_to_invoice.write({'partner_id': test_customer.id})
            return_to_invoice.action_pos_order_invoice()
            # Check the credit note
            self.assertTrue(return_to_invoice.account_move, 'Invoice should be created.')
            self.assertEqual(return_to_invoice.account_move.move_type, 'out_refund', 'Invoice should be a credit note.')
            self.assertEqual(return_to_invoice.account_move.invoice_date, new_session_date.date(), 'Invoice date should be the same as the session it is created in.')
            self.assertRecordValues(return_to_invoice.account_move, [{
                'amount_untaxed': 30,
                'amount_tax': 0,
                'amount_total': 30,
            }])
            self.assertRecordValues(return_to_invoice.account_move.line_ids, [
                {'account_id': self.sales_account.id, 'balance': 30},
                {'account_id': self.receivable_account.id, 'balance': -30},
            ])

    def test_invoice_past_order(self):
        # create 1 uninvoiced order then close the session
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product99, 1)], 'payments': [(self.bank_pm1, 99)], 'customer': False, 'is_invoiced': False, 'uuid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 99, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 99, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [
                    ((99, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 99, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 99, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

        # keep reference of the closed session
        closed_session = self.pos_session
        self.assertTrue(closed_session.state == 'closed', 'Session should be closed.')

        order_to_invoice = closed_session.order_ids[0]
        test_customer = self.env['res.partner'].create({'name': 'Test Customer'})

        with freeze_time(fields.Datetime.now() + relativedelta(days=2)):
            # create new session after 2 days
            self.open_new_session(0)
            # invoice the uninvoiced order
            order_to_invoice.write({'partner_id': test_customer.id})
            order_to_invoice.action_pos_order_invoice()
            # check invoice
            invoice = order_to_invoice.account_move
            self.assertTrue(invoice, 'Invoice should be created.')
            self.assertNotEqual(invoice.invoice_date, order_to_invoice.date_order.date(), 'Invoice date should not be the same as order date since the session was closed.')

            # check that the payment date is set to the order date which
            # is the real payment date and not to the invoice_date
            payment = invoice.line_ids.full_reconcile_id.reconciled_line_ids.move_id - invoice
            self.assertEqual(payment.date, order_to_invoice.date_order.date())

    def test_invoice_past_order_affecting_taxes(self):
        """ Test whether two taxes affecting each other don't trigger a recomputation on invoice generation
        """
        # Create 1 uninvoiced order then close the session
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product_multi_tax, 1)], 'payments': [(self.bank_pm1, 117.72)], 'customer': False, 'is_invoiced': False, 'uuid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.tax_received_account.id, 'partner_id': False, 'debit': 0, 'credit': 8, 'reconciled': False},
                        {'account_id': self.tax_received_account.id, 'partner_id': False, 'debit': 0, 'credit': 9.72, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 117.72, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [
                    ((117.72, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 117.72, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 117.72, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

        closed_session = self.pos_session
        self.assertTrue(closed_session.state == 'closed', 'Session should be closed.')

        order_to_invoice = closed_session.order_ids[0]
        test_customer = self.env['res.partner'].create({'name': 'Test Customer'})

        # Create a new session
        self.open_new_session(0)
        # Invoice the uninvoiced order
        order_to_invoice.write({'partner_id': test_customer.id})
        order_to_invoice.action_pos_order_invoice()
        # Check the invoice for the lines
        self.assertTrue(order_to_invoice.account_move, 'Invoice should be created.')
        self.assertRecordValues(order_to_invoice.account_move.line_ids, [
            {'account_id': self.sales_account.id, 'balance': -100, 'reconciled': False},
            {'account_id': self.tax_received_account.id, 'balance': -8, 'reconciled': False},
            {'account_id': self.tax_received_account.id, 'balance': -9.72, 'reconciled': False},
            {'account_id': self.receivable_account.id, 'balance': 117.72, 'reconciled': True},
        ])

    def test_invoice_past_refund(self):
        """ Test invoicing a past refund

        Orders
        ======
        +------------------+----------+-----------+----------+-----+-------+
        | order            | payments | invoiced? | product  | qty | total |
        +------------------+----------+-----------+----------+-----+-------+
        | order 1          | cash     | no        | product3 |   1 |    30 |
        +------------------+----------+-----------+----------+-----+-------+
        | order 2 (return) | cash     | no        | product3 |  -1 |   -30 |
        +------------------+----------+-----------+----------+-----+-------+

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | sale (sales)        |     -30 |
        | sale (refund)       |      30 |
        +---------------------+---------+
        | Total balance       |     0.0 |
        +---------------------+---------+
        """
        def _before_closing_cb():
            # Return the order
            order_to_return = self.pos_session.order_ids.filtered(lambda order: '12345-123-1234' in order.uuid)
            order_to_return.refund()
            refund_order = self.pos_session.order_ids.filtered(lambda order: order.state == 'draft')

            # Check if there's an amount to pay
            self.assertAlmostEqual(refund_order.amount_total - refund_order.amount_paid, -30)

            # Pay the refund
            context_make_payment = {"active_ids": [refund_order.id], "active_id": refund_order.id}
            make_payment = self.env['pos.make.payment'].with_context(context_make_payment).create({
                'payment_method_id': self.cash_pm1.id,
                'amount': -30,
            })
            make_payment.check()

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product3, 1)], 'payments': [(self.cash_pm1, 30)], 'uuid': '12345-123-1234'},
            ],
            'before_closing_cb': _before_closing_cb,
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 30, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 30, 'credit': 0, 'reconciled': False},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [],
            },
        })

        closed_session = self.pos_session
        self.assertTrue(closed_session.state == 'closed', 'Session should be closed.')

        return_to_invoice = closed_session.order_ids[1]
        test_customer = self.env['res.partner'].create({'name': 'Test Customer'})
        new_session_date = return_to_invoice.date_order + relativedelta(days=2)

        with freeze_time(new_session_date):
            # Create a new session after 2 days
            self.open_new_session(0)
            # Invoice the uninvoiced refund
            return_to_invoice.write({'partner_id': test_customer.id})
            return_to_invoice.action_pos_order_invoice()
            # Check the credit note
            self.assertTrue(return_to_invoice.account_move, 'Invoice should be created.')
            self.assertEqual(return_to_invoice.account_move.move_type, 'out_refund', 'Invoice should be a credit note.')
            self.assertEqual(return_to_invoice.account_move.invoice_date, new_session_date.date(), 'Invoice date should be the same as the session it is created in.')
            self.assertRecordValues(return_to_invoice.account_move, [{
                'amount_untaxed': 30,
                'amount_tax': 0,
                'amount_total': 30,
            }])
            self.assertRecordValues(return_to_invoice.account_move.line_ids, [
                {'account_id': self.sales_account.id, 'balance': 30},
                {'account_id': self.receivable_account.id, 'balance': -30},
            ])

    def test_invoice_past_order(self):
        # create 1 uninvoiced order then close the session
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product99, 1)], 'payments': [(self.bank_pm1, 99)], 'customer': False, 'is_invoiced': False, 'uuid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 99, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 99, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [
                    ((99, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 99, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 99, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

        # keep reference of the closed session
        closed_session = self.pos_session
        self.assertTrue(closed_session.state == 'closed', 'Session should be closed.')

        order_to_invoice = closed_session.order_ids[0]
        test_customer = self.env['res.partner'].create({'name': 'Test Customer'})

        with freeze_time(fields.Datetime.now() + relativedelta(days=2)):
            # create new session after 2 days
            self.open_new_session(0)
            # invoice the uninvoiced order
            order_to_invoice.write({'partner_id': test_customer.id})
            order_to_invoice.action_pos_order_invoice()
            # check invoice
            invoice = order_to_invoice.account_move
            self.assertTrue(invoice, 'Invoice should be created.')
            self.assertNotEqual(invoice.invoice_date, order_to_invoice.date_order.date(), 'Invoice date should not be the same as order date since the session was closed.')

            # check that the payment date is set to the order date which
            # is the real payment date and not to the invoice_date
            payment = invoice.line_ids.full_reconcile_id.reconciled_line_ids.move_id - invoice
            self.assertEqual(payment.date, order_to_invoice.date_order.date())

    def test_invoice_past_order_affecting_taxes(self):
        """ Test whether two taxes affecting each other don't trigger a recomputation on invoice generation
        """
        # Create 1 uninvoiced order then close the session
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product_multi_tax, 1)], 'payments': [(self.bank_pm1, 117.72)], 'customer': False, 'is_invoiced': False, 'uuid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.tax_received_account.id, 'partner_id': False, 'debit': 0, 'credit': 8, 'reconciled': False},
                        {'account_id': self.tax_received_account.id, 'partner_id': False, 'debit': 0, 'credit': 9.72, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 117.72, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [
                    ((117.72, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 117.72, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 117.72, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

        closed_session = self.pos_session
        self.assertTrue(closed_session.state == 'closed', 'Session should be closed.')

        order_to_invoice = closed_session.order_ids[0]
        test_customer = self.env['res.partner'].create({'name': 'Test Customer'})

        # Create a new session
        self.open_new_session(0)
        # Invoice the uninvoiced order
        order_to_invoice.write({'partner_id': test_customer.id})
        order_to_invoice.action_pos_order_invoice()
        # Check the invoice for the lines
        self.assertTrue(order_to_invoice.account_move, 'Invoice should be created.')
        self.assertRecordValues(order_to_invoice.account_move.line_ids, [
            {'account_id': self.sales_account.id, 'balance': -100, 'reconciled': False},
            {'account_id': self.tax_received_account.id, 'balance': -8, 'reconciled': False},
            {'account_id': self.tax_received_account.id, 'balance': -9.72, 'reconciled': False},
            {'account_id': self.receivable_account.id, 'balance': 117.72, 'reconciled': True},
        ])

    def _get_loaded_product_ids(self, session):
        data = session.load_data([])
        special_product = session.config_id._get_special_products().ids
        return [p['product_variant_ids'][0] for p in data['product.template']
                if p['product_variant_ids'][0] not in special_product]

    def test_limited_products_loading(self):
        """
        This test makes sure that the limited products loading feature loads
        at most `point_of_sale.limited_product_count` product templates,
        regardless of which specific criteria decides which ones make the
        cut. That ordering is a separate concern which can be overridden by
        other modules.
        """
        # Restrict the loaded-product domain to our own POS category so any
        # other available_in_pos product (demo data, combos, setUp fixtures)
        # never competes for the limited slots.
        test_categ = self.env['pos.category'].create({'name': 'Limited Loading Test Category'})
        self.config.write({
            'limit_categories': True,
            'iface_available_categ_ids': [(6, 0, test_categ.ids)],
        })
        products = self.env['product.product']
        for i in range(5):
            products |= self.create_product(f'Count Product {i}', self.categ_basic, 10)
        products.product_tmpl_id.write({'pos_categ_ids': [(6, 0, test_categ.ids)]})
        self.env['ir.config_parameter'].sudo().set_int('point_of_sale.limited_product_count', 3)
        self.env.flush_all()
        session = self.open_new_session(0)

        self.assertEqual(len(self._get_loaded_product_ids(session)), 3)

    def test_limited_products_loading_priority(self):
        """
        This test makes sure that our limited products loading feature
        prioritizes product templates in this order, with ties being broken
        by the next trait:
        1st. "Favorited" products (is_favorite)
        2nd. "Service" type products (type)
        3rd. Recently written to products (write_date)
        """
        if 'pos_stock' in self.env['ir.module.module']._installed():
            self.skipTest(
                "The module pos_stock is installed and defines a conflicting ordering.")
        # Restrict the loaded-product domain to our own POS category so any
        # other available_in_pos product (demo data, combos, setUp fixtures)
        # never competes for the limited spots.
        test_categ = self.env['pos.category'].create({'name': 'Priority Test Category'})
        self.config.write({
            'limit_categories': True,
            'iface_available_categ_ids': [(6, 0, test_categ.ids)],
        })
        product0 = self.create_product('Priority Product 0', self.categ_basic, 10)
        product1 = self.create_product('Priority Product 1', self.categ_basic, 10)
        product2 = self.create_product('Priority Product 2', self.categ_basic, 10)
        product3 = self.create_product('Priority Product 3', self.categ_basic, 10)
        product4 = self.create_product('Priority Product 4', self.categ_basic, 10)
        (product0 | product1 | product2 | product3 | product4).product_tmpl_id.write({
            'pos_categ_ids': [(6, 0, test_categ.ids)],
        })
        product2.product_tmpl_id.write({"is_favorite": True, "type": "consu"})
        product3.product_tmpl_id.write({"is_favorite": False, "type": "service"})
        product4.product_tmpl_id.write({"is_favorite": False, "type": "consu"})

        # product0 and product1 are tied on (is_favorite, type); only
        # write_date should decide between them.
        now = fields.Datetime.now()
        self.patch(self.env.cr, 'now', lambda: now - relativedelta(minutes=1))
        product1.product_tmpl_id.write({"is_favorite": True, "type": "service"})
        self.env.flush_all()
        self.patch(self.env.cr, 'now', lambda: now)
        product0.product_tmpl_id.write({"is_favorite": True, "type": "service"})
        self.env.flush_all()

        session = self.open_new_session(0)

        def loaded_ids(limit):
            self.env['ir.config_parameter'].sudo().set_int('point_of_sale.limited_product_count', limit)
            return self._get_loaded_product_ids(session)

        # write_date breaks the tie between product0 and product1.
        self.assertCountEqual(loaded_ids(1), [product0.id])
        # is_favorite outranks type: both favorited products beat any non-favorite.
        self.assertCountEqual(loaded_ids(3), [product0.id, product1.id, product2.id])
        # type breaks ties among non-favorited products too.
        self.assertCountEqual(loaded_ids(4), [product0.id, product1.id, product2.id, product3.id])

    def test_pos_payment_method_copy(self):
        """
        Test POS payment method copy:
            - Create two payment methods in which one of the payment method's journal type be cash
            - Copy multiple payment methods
            - Check the duplicated cash payment method journal should be empty
        """
        pm_1 = self.cash_pm1
        pm_2 = self.bank_pm1
        pm_3, pm_4 = (pm_1 + pm_2).copy()

        self.assertTrue(pm_3)
        self.assertFalse(pm_3.journal_id)
        self.assertTrue(pm_4)
        self.assertEqual(pm_4.journal_id.type, "bank")

    def test_single_config_global_invoice(self):
        """For a single POS config, create multiple orders and consolidate them into a single invoice"""
        self.open_new_session()
        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product1, 2), (self.product4, 3)],
            payments=[(self.bank_pm1, 49.88)]
        ))
        orders.append(self.create_ui_order_data(
            [(self.product4, 1), (self.product2, 5)],
            payments=[(self.bank_pm1, 109.96)]
        ))

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)
        # close the session
        self.pos_session.close_session_from_ui()

        pos_orders = self.env['pos.order'].search([])
        # set customer for the orders
        pos_orders.write({'partner_id': self.customer.id})

        # create consolidated invoice
        self.env['pos.make.invoice'].create({
            "consolidated_billing": True,
        }).with_context({
            "active_ids": pos_orders.ids,
        }).action_create_invoices()
        # check if have single invoice
        self.assertEqual(len(pos_orders), 2)
        self.assertEqual(len(pos_orders.account_move), 1)
        self.assertEqual(pos_orders.account_move.partner_id, self.customer)
        self.assertEqual(pos_orders.account_move.amount_total, sum(pos_orders.mapped('amount_total')))
        self.assertEqual(pos_orders.account_move.payment_state, pos_orders.account_move._get_invoice_in_payment_state())
        self.assertEqual(pos_orders.account_move.state, 'posted')
        self.assertEqual(pos_orders.account_move.amount_residual, 0)

    def test_multi_config_global_invoice(self):
        self.open_new_session()
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product1, 3), (self.product2, 10)],
            payments=[(self.bank_pm1, 230)]
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, 5), (self.product0, 10)],
            payments=[(self.bank_pm1, 50)]
        ))
        self.env['pos.order'].sync_from_ui(orders)
        self.pos_session.close_session_from_ui()

        # open new session & create orders
        self.open_new_session()
        orders2 = []
        orders2.append(self.create_ui_order_data(
            [(self.product1, 2), (self.product4, 3)],
            payments=[(self.bank_pm1, 49.88)]
        ))
        orders2.append(self.create_ui_order_data(
            [(self.product4, 1), (self.product2, 5)],
            payments=[(self.bank_pm1, 109.96)]
        ))
        self.env['pos.order'].sync_from_ui(orders2)
        self.pos_session.close_session_from_ui()

        pos_orders = self.env['pos.order'].search([])
        # set customer for the orders
        pos_orders.write({'partner_id': self.customer.id})

        # create consolidated invoice
        self.env['pos.make.invoice'].create({
            "consolidated_billing": True,
        }).with_context({
            "active_ids": pos_orders.ids,
        }).action_create_invoices()
        # check if have single invoice
        self.assertEqual(len(pos_orders), 4)
        self.assertTrue(all(order.state == 'done' for order in pos_orders))
        self.assertEqual(len(pos_orders.account_move), 1)
        self.assertNotEqual(self.pos_session.move_ids, pos_orders.account_move)
        self.assertEqual(pos_orders.account_move.partner_id, self.customer)
        self.assertEqual(pos_orders.account_move.amount_total, round(sum(pos_orders.mapped('amount_total')), 2))
        self.assertEqual(pos_orders.account_move.payment_state, pos_orders.account_move._get_invoice_in_payment_state())
        self.assertEqual(pos_orders.account_move.state, 'posted')
        self.assertEqual(pos_orders.account_move.amount_residual, 0)

    def test_pos_archived_combination(self):
        product = self.env['product.template'].create({
            'name': 'Product Test',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': False,
        })

        attribute_1, attribute_2, attribute_3 = self.env['product.attribute'].create([{
            'name': 'Attribute 1',
            'create_variant': 'always',
            'value_ids': [(0, 0, {
                'name': 'Value 1',
            }), (0, 0, {
                'name': 'Value 2',
            })],
        }, {
            'name': 'Attribute 2',
            'create_variant': 'always',
            'value_ids': [(0, 0, {
                'name': 'Value 1',
            }), (0, 0, {
                'name': 'Value 2',
            })],
        }, {
            'name': 'Attribute 3',
            'create_variant': 'always',
            'value_ids': [(0, 0, {
                'name': 'Value 1',
            }), (0, 0, {
                'name': 'Value 2',
            })],
        }])

        _, _, ptal = self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': product.id,
            'attribute_id': attribute_1.id,
            'value_ids': [(6, 0, attribute_1.value_ids.ids)],
            'sequence': 3,
        }, {
            'product_tmpl_id': product.id,
            'attribute_id': attribute_2.id,
            'value_ids': [(6, 0, attribute_2.value_ids.ids)],
            'sequence': 2,
        }, {
            'product_tmpl_id': product.id,
            'attribute_id': attribute_3.id,
            'value_ids': [(6, 0, attribute_3.value_ids.ids)],
            'sequence': 1,
        }])

        product.write({
            'attribute_line_ids': [(2, ptal.id)],
        })

        self.open_new_session()
        response = self.pos_session.load_data([])
        product_data = next((item for item in response['product.template'] if item['id'] == product.id), None)

        self.assertEqual(len(product_data['_archived_combinations']), 0, "There should be no archived combinations for the product")

        first_variant = product.product_variant_ids[0]
        first_variant.write({'active': False})

        response = self.pos_session.load_data([])
        product_data = next((item for item in response['product.template'] if item['id'] == product.id), None)

        self.assertEqual(len(product_data['_archived_combinations']), 1, "There should be one archived combination for the product")
        self.assertEqual(len(product_data['_archived_combinations'][0]), 2, "Archived combination should have two values")
        self.assertTrue(all(value in product_data['_archived_combinations'][0] for value in first_variant.product_template_attribute_value_ids.ids), "Archived combination should match the first variant's attribute values")

    def test_refunded_order_id(self):
        """
        An order containing refunded lines from two different orders is no longer allowed,
        but some legacy records of this kind may still exist.
        This test ensures that the refunded_order_id is correctly computed in such cases.
        """
        current_session = self.open_new_session()
        orders = list(self._create_orders([
            {'pos_order_lines_ui_args': [(self.product1, 1)]},
            {'pos_order_lines_ui_args': [(self.product2, 1)]}
        ]).values())

        refund_order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'lines': [
                (0, 0, {
                    'product_id': self.product1.id,
                    'price_unit': -10,
                    'qty': 1,
                    'tax_ids': [[6, False, []]],
                    'price_subtotal': -10,
                    'price_subtotal_incl': -10,
                    'refunded_orderline_id': orders[0].lines[0].id
                }),
                (0, 0, {
                    'product_id': self.product2.id,
                    'price_unit': -10,
                    'qty': 1,
                    'tax_ids': [[6, False, []]],
                    'price_subtotal': -10,
                    'price_subtotal_incl': -10,
                    'refunded_orderline_id': orders[1].lines[0].id
                })
            ],
            'amount_paid': -10,
            'amount_total': -10,
            'amount_tax': 0.0,
            'amount_return': 0.0,
        })

        self.assertEqual(refund_order.refunded_order_id, orders[0])

    def test_cannot_archive_journal_linked_to_pos_payment_method(self):
        """Test that archiving a journal linked to a POS payment method is blocked, and allowed when not linked."""

        test_journal = self.env['account.journal'].create({
            'name': 'Test POS Journal',
            'type': 'cash',
            'code': 'TPJ',
            'company_id': self.env.company.id,
        })
        test_payment_method = self.env['pos.payment.method'].create({
            'name': 'Test PM',
            'type': 'cash',
            'journal_id': test_journal.id,
            'receivable_account_id': self.cash_pm1.receivable_account_id.id,
        })

        with self.assertRaises(ValidationError):
            test_journal.action_archive()

        # Unlink the payment method and try again (should succeed)
        test_payment_method.journal_id = False
        test_journal.action_archive()
        self.assertFalse(test_journal.active, "Journal should be archived when not linked to a POS payment method.")

    def test_archive_delete_special_product(self):
        self.config.iface_tipproduct = True
        special_product = self.env.ref('point_of_sale.product_product_tip')
        with self.assertRaisesRegex(UserError, "a special product in a Point of Sale configuration"):
            special_product.action_archive()
        with self.assertRaisesRegex(UserError, "a special product in a Point of Sale configuration"):
            special_product.product_variant_ids[0].action_archive()
        with self.assertRaisesRegex(UserError, "a special product in a Point of Sale configuration"):
            special_product.unlink()
        with self.assertRaisesRegex(UserError, "a special product in a Point of Sale configuration"):
            special_product.product_variant_ids[0].unlink()

    def test_pos_invoice_not_to_review_pos_only_user(self):
        """POS invoices must not be 'marked as 'to review' even when
        the invoicing user has no accounting review permissions."""
        self.open_new_session()

        pos_only_user = self.env['res.users'].create({
            'name': 'POS Only User',
            'login': 'pos_only_user',
            'password': 'pos_only_user',
            'group_ids': [self.env.ref('point_of_sale.group_pos_manager').id],
        })

        orders = self._create_orders([{
            'pos_order_lines_ui_args': [(self.product1, 1)],
            'customer': self.customer,
            'is_invoiced': False,
        }])
        orders = sum(orders.values(), self.env['pos.order'])

        orders.with_user(pos_only_user)._generate_pos_order_invoice()

        self.assertEqual(orders.account_move.review_state, 'no_review')

    def test_delete_archive_product_pos_category_with_active_pos_session(self):
        self.env['pos.session'].search([('state', '!=', 'closed')]).state = "closed"
        category1 = self.env['pos.category'].create({'name': 'Category 1'})
        category2 = self.env['pos.category'].create({'name': 'Category 2'})

        product1 = self.create_product('Product 1', self.categ_basic, 0.0, 0.0)
        product2 = self.create_product('Product 2', self.categ_basic, 0.0, 0.0)

        product1.pos_categ_ids = [(6, 0, [category1.id])]
        product2.pos_categ_ids = [(6, 0, [category2.id])]

        # Open unrestricted session -> everything protected.
        self.basic_config.open_ui()
        self.basic_config.iface_available_categ_ids = []

        with self.assertRaisesRegex(UserError, "active Point of Sale session"):
            product2.action_archive()

        with self.assertRaisesRegex(UserError, "active Point of Sale session"):
            category2.unlink()

        # Open restricted session for category1 only.
        self.basic_config.iface_available_categ_ids = [(6, 0, [category1.id])]

        # category1/product1 still protected.
        with self.assertRaisesRegex(UserError, "active Point of Sale session"):
            product1.product_variant_id.action_archive()

        with self.assertRaisesRegex(UserError, "currently in use in a point of sale"):
            category1.action_archive()

        # category2/product2 no longer protected.
        product2.action_archive()
        product2.unlink()

        category2.action_archive()
        category2.unlink()

        # After session close, only config protection remains.
        self.basic_config.current_session_id.state = 'closed'

        with self.assertRaisesRegex(UserError, "currently in use in a point of sale"):
            category1.unlink()
