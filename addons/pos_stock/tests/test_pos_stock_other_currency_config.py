# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest import skip

from odoo.addons.pos_stock.tests.common import TestPosStockCommon


class TestPoSOtherCurrencyConfig(TestPosStockCommon):
    """ Test PoS with basic configuration
    """

    def setUp(self):
        super().setUp()
        self.config = self.other_currency_config
        self.product4 = self.create_product('Product 4', self.categ_anglo, 100, 50)
        self.product5 = self.create_product('Product 5', self.categ_anglo, 200, 70)
        self.product6 = self.create_product('Product 6', self.categ_anglo, 45.3, 10.73)
        self.expense_account = self.categ_anglo.property_account_expense_categ_id

    def test_01_check_product_cost(self):
        # Product price should be half of the original price because currency rate is 0.5.
        # (see `self._create_other_currency_config` method)
        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product4, 1), 50)
        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product5, 1), 100)
        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product6, 1), 22.65)

    @skip('Temporary to fast merge new valuation')
    def test_04_anglo_saxon_products(self):
        """
        ======
        Orders
        ======
        +---------+----------+-----------+----------+-----+----------+------------+
        | order   | payments | invoiced? | product  | qty |    total | total cost |
        |         |          |           |          |     |          |            |
        +---------+----------+-----------+----------+-----+----------+------------+
        | order 1 | cash     | no        | product4 |   7 |      700 |        350 |
        |         |          |           | product5 |   7 |     1400 |        490 |
        +---------+----------+-----------+----------+-----+----------+------------+
        | order 2 | cash     | no        | product5 |   6 |     1200 |        420 |
        |         |          |           | product4 |   6 |      600 |        300 |
        |         |          |           | product6 |  49 |   2219.7 |     525.77 |
        +---------+----------+-----------+----------+-----+----------+------------+
        | order 3 | cash     | no        | product5 |   2 |      400 |        140 |
        |         |          |           | product6 |  13 |    588.9 |     139.49 |
        +---------+----------+-----------+----------+-----+----------+------------+
        | order 4 | cash     | no        | product6 |   1 |     45.3 |      10.73 |
        +---------+----------+-----------+----------+-----+----------+------------+

        ===============
        Expected Result
        ===============
        +---------------------+------------+-----------------+
        | account             |    balance | amount_currency |
        +---------------------+------------+-----------------+
        | sale_account        |   -7153.90 |        -3576.95 |
        | pos_receivable-cash |    7153.90 |         3576.95 |
        | expense_account     |    2375.99 |         2375.99 |
        | output_account      |   -2375.99 |        -2375.99 |
        +---------------------+------------+-----------------+
        | Total balance       |       0.00 |            0.00 |
        +---------------------+------------+-----------------+
        """

        self._run_test({
            'payment_methods': self.cash_pm2,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product4, 7), (self.product5, 7)], 'uuid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product5, 6), (self.product4, 6), (self.product6, 49)], 'uuid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product5, 2), (self.product6, 13)], 'uuid': '00100-010-0003'},
                {'pos_order_lines_ui_args': [(self.product6, 1)], 'uuid': '00100-010-0004'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 7153.90, 'reconciled': False, 'amount_currency': -3576.95},
                        {'account_id': self.expense_account.id, 'partner_id': False, 'debit': 2375.99, 'credit': 0, 'reconciled': False, 'amount_currency': 2375.99},
                        {'account_id': self.cash_pm2.receivable_account_id.id, 'partner_id': False, 'debit': 7153.90, 'credit': 0, 'reconciled': True, 'amount_currency': 3576.95},
                        {'account_id': self.output_account.id, 'partner_id': False, 'debit': 0, 'credit': 2375.99, 'reconciled': True, 'amount_currency': -2375.99},
                    ],
                },
                'cash_statement': [
                    ((3576.95, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm2.journal_id.default_account_id.id, 'partner_id': False, 'debit': 7153.90, 'credit': 0, 'reconciled': False, 'amount_currency': 3576.95},
                            {'account_id': self.cash_pm2.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 7153.90, 'reconciled': True, 'amount_currency': -3576.95},
                        ]
                    }),
                ],
                'bank_payments': [],
            },
        })

    def test_with_session_check_product_cost(self):
        def find_by(list_of_dicts, key, value):
            return next((d for d in list_of_dicts if d.get(key) == value), None)

        self.other_currency_config.open_ui()
        product = self.other_currency_config.current_session_id.load_data([])['product.product']

        self.assertAlmostEqual(find_by(product, 'id', self.product4.id)['lst_price'], 50.00)
        self.assertAlmostEqual(find_by(product, 'id', self.product5.id)['lst_price'], 100.00)
        self.assertAlmostEqual(find_by(product, 'id', self.product6.id)['lst_price'], 22.65)
