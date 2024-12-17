import uuid

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.common import TestSaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrderDownPayment(TestSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.other_currency = cls.setup_other_currency('EUR')

        SaleOrder = cls.env['sale.order']

        cls.tax_account = cls.env['account.account'].search([('account_type', '=', 'liability_current')], limit=1)
        cls.tax_10 = cls.create_tax(10)
        cls.tax_15 = cls.create_tax(15)

        # create a generic Sale Order with all classical products and empty pricelist
        cls.sale_order = SaleOrder.create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
        })
        cls.sol_product_order = cls.env['sale.order.line'].create({
            'name': cls.company_data['product_order_no'].name,
            'product_id': cls.company_data['product_order_no'].id,
            'product_uom_qty': 2,
            'price_unit': 100,
            'order_id': cls.sale_order.id,
            'tax_ids': False,
        })
        cls.sol_serv_deliver = cls.env['sale.order.line'].create({
            'name': cls.company_data['product_service_delivery'].name,
            'product_id': cls.company_data['product_service_delivery'].id,
            'product_uom_qty': 2,
            'price_unit': 100,
            'order_id': cls.sale_order.id,
            'tax_ids': False,
        })
        cls.sol_serv_order = cls.env['sale.order.line'].create({
            'name': cls.company_data['product_service_order'].name,
            'product_id': cls.company_data['product_service_order'].id,
            'product_uom_qty': 2,
            'price_unit': 100,
            'order_id': cls.sale_order.id,
            'tax_ids': False,
        })
        cls.sol_product_deliver = cls.env['sale.order.line'].create({
            'name': cls.company_data['product_delivery_no'].name,
            'product_id': cls.company_data['product_delivery_no'].id,
            'product_uom_qty': 2,
            'price_unit': 100,
            'order_id': cls.sale_order.id,
            'tax_ids': False,
        })

        cls.revenue_account = cls.company_data['default_account_revenue']
        cls.receivable_account = cls.company_data['default_account_receivable']

    @classmethod
    def create_tax(cls, amount, values=None):
        vals = {
            'name': f'Tax {amount} {uuid.uuid4()}',
            'amount_type': 'percent',
            'amount': amount,
            'type_tax_use': 'sale',
            'repartition_line_ids': [
                Command.create({'document_type': 'invoice', 'repartition_type': 'base'}),
                Command.create({'document_type': 'invoice', 'repartition_type': 'tax', 'account_id': cls.tax_account.id}),
                Command.create({'document_type': 'refund', 'repartition_type': 'base'}),
                Command.create({'document_type': 'refund', 'repartition_type': 'tax', 'account_id': cls.tax_account.id}),
            ]
        }
        if values:
            vals.update(values)
        return cls.env['account.tax'].create(vals)

    @classmethod
    def make_downpayment(cls, **kwargs):
        so_context = {
            'active_model': 'sale.order',
            'active_ids': [cls.sale_order.id],
            'active_id': cls.sale_order.id,
            'default_journal_id': cls.company_data['default_journal_sale'].id,
        }
        payment_params = {
            'advance_payment_method': 'percentage',
            'amount': 50,
            **kwargs,
        }
        downpayment = cls.env['sale.advance.payment.inv'].with_context(so_context).create(payment_params)
        downpayment.create_invoices()
        if cls.sale_order.state == 'draft':
            cls.sale_order.action_confirm()

    def _assert_invoice_lines_values(self, lines, expected):
        return self.assertRecordValues(lines, [dict(zip(expected[0], x)) for x in expected[1:]])

    def test_tax_and_account_breakdown(self):
        income_acc_2 = self.revenue_account.copy()
        self.sale_order.order_line[1].product_id.product_tmpl_id.property_account_income_id = income_acc_2

        self.sale_order.order_line[0].tax_ids = self.tax_15 + self.tax_10
        self.sale_order.order_line[1].tax_ids = self.tax_10
        self.sale_order.order_line[2].tax_ids = self.tax_10
        self.make_downpayment()
        invoice = self.sale_order.invoice_ids
        down_pay_amt = self.sale_order.amount_total / 2
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                      'balance',     'price_total'],
            # base lines
            [self.revenue_account.id,    (self.tax_15 + self.tax_10).ids, -100,         125          ],
            [income_acc_2.id,            self.tax_10.ids,                 -100,         110          ],
            [self.revenue_account.id,    self.tax_10.ids,                 -100,         110          ],
            [self.revenue_account.id,    self.env['account.tax'],         -100,         100          ],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],         -30,          0            ],
            [self.tax_account.id,        self.env['account.tax'],         -15,          0            ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],         down_pay_amt, 0            ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)
        invoice.action_post()

        # Deliver product_service_delivery and product_delivery_no
        self.sale_order.order_line[1].qty_delivered = 2
        self.sale_order.order_line[3].qty_delivered = 2

        # Full Invoice
        invoicing_wizard = self.env['sale.advance.payment.inv'].create({
            'sale_order_ids': [Command.link(self.sale_order.id)],
            'advance_payment_method': 'delivered',
        })
        action = invoicing_wizard.create_invoices()
        full_invoice = self.env['account.move'].browse(action['res_id'])
        # pylint: disable=C0326
        full_invoice_expected = [
            # keys
            ['account_id',               'tax_ids',                      'balance',     'price_total'],
            # product lines
            [self.revenue_account.id,    (self.tax_15 + self.tax_10).ids, -200,         250          ],
            [income_acc_2.id,            self.tax_10.ids,                 -200,         220          ],
            [self.revenue_account.id,    self.tax_10.ids,                 -200,         220          ],
            [self.revenue_account.id,    self.env['account.tax'],         -200,         200          ],
            # downpayment section
            [False,                      [],                              0,            0            ],
            # deduction downpayment lines
            [self.revenue_account.id,    (self.tax_15 + self.tax_10).ids, 100,          -125         ],
            [income_acc_2.id,            self.tax_10.ids,                 100,          -110         ],
            [self.revenue_account.id,    self.tax_10.ids,                 100,          -110         ],
            [self.revenue_account.id,    self.env['account.tax'],         100,          -100         ],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],         -30,          0            ],
            [self.tax_account.id,        self.env['account.tax'],         -15,          0            ],
            # receivable (same as dwonpayment since downpayment 50%)
            [self.receivable_account.id, self.env['account.tax'],         down_pay_amt, 0            ],
        ]
        self._assert_invoice_lines_values(full_invoice.line_ids, full_invoice_expected)

    def test_tax_with_diff_tax_on_invoice_breakdown(self):
        # if a generated invoice has it's taxes changed, this should not affect the next downpayment on an SO
        self.sale_order.order_line[0].tax_ids = self.tax_15
        (self.sale_order.order_line - self.sale_order.order_line[0]).unlink()
        self.make_downpayment(amount=25)
        first_invoice = self.sale_order.invoice_ids
        first_invoice.invoice_line_ids.tax_ids = None
        first_invoice.action_post()
        self.make_downpayment(amount=25)
        invoice = self.sale_order.invoice_ids - first_invoice
        down_pay_amt = self.sale_order.amount_total / 4
        # ruff: noqa: E202
        expected = [
            # keys
            ['account_id',               'tax_ids',               'balance',   'price_total'],
            # base lines
            [self.revenue_account.id,    self.tax_15.ids,         -50,          57.5        ],
            # taxes
            [self.tax_account.id,        self.env['account.tax'], -7.5,         0           ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'], down_pay_amt, 0           ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_breakdown_other_currency(self):
        self.sale_order.currency_id = self.other_currency  # rate = 2.0
        self.sale_order.order_line[0].tax_ids = self.tax_15 + self.tax_10
        self.sale_order.order_line[1].tax_ids = self.tax_10
        self.sale_order.order_line[2].tax_ids = self.tax_10
        self.make_downpayment()
        invoice = self.sale_order.invoice_ids
        down_pay_amt = self.sale_order.amount_total / 2
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                      'balance',           'price_total'],
            # base lines
            [self.revenue_account.id,    (self.tax_15 + self.tax_10).ids, -50,                125          ],
            [self.revenue_account.id,    self.tax_10.ids,                 -100,               220          ],
            [self.revenue_account.id,    self.env['account.tax'],         -50,                100          ],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],         -15,                0            ],
            [self.tax_account.id,        self.env['account.tax'],         -7.5,               0            ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],         down_pay_amt / 2.0, 0            ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_breakdown_fixed_payment_method(self):
        self.sale_order.order_line[0].tax_ids = self.tax_15 + self.tax_10
        self.sale_order.order_line[1].tax_ids = self.tax_10
        self.sale_order.order_line[2].tax_ids = self.tax_10
        self.make_downpayment(advance_payment_method='fixed', fixed_amount=222.5, amount=0)
        invoice = self.sale_order.invoice_ids
        down_pay_amt = 222.5
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                      'balance',     'price_total'],
            # base lines
            [self.revenue_account.id,    (self.tax_15 + self.tax_10).ids, -50,          62.5         ],
            [self.revenue_account.id,    self.tax_10.ids,                 -100,         110          ],
            [self.revenue_account.id,    self.env['account.tax'],         -50,          50           ],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],         -15,          0            ],
            [self.tax_account.id,        self.env['account.tax'],         -7.5,         0            ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],         down_pay_amt, 0            ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_breakdown_fixed_payment_method_with_taxes_on_all_lines(self):
        self.sale_order.order_line[0].tax_ids = self.tax_15
        self.sale_order.order_line[1].tax_ids = self.tax_10
        self.sale_order.order_line[2].tax_ids = self.tax_10
        self.sale_order.order_line[3].tax_ids = self.tax_10
        self.make_downpayment(advance_payment_method='fixed', fixed_amount=222.5, amount=0)
        invoice = self.sale_order.invoice_ids
        down_pay_amt = 222.5
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',              'balance',     'price_total'],
            # base lines
            [self.revenue_account.id,    self.tax_15.ids,         -50,          57.5         ],
            [self.revenue_account.id,    self.tax_10.ids,         -150,         165          ],
            # taxes
            [self.tax_account.id,        self.env['account.tax'], -7.5,         0            ],
            [self.tax_account.id,        self.env['account.tax'], -15,          0            ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'], down_pay_amt, 0            ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_price_include_breakdown(self):
        tax_10_incl = self.create_tax(10, {'price_include_override': 'tax_included'})
        self.sale_order.order_line[0].tax_ids = tax_10_incl + self.tax_10
        self.sale_order.order_line[1].tax_ids = self.tax_10
        self.sale_order.order_line[2].tax_ids = self.tax_10
        self.make_downpayment()
        invoice = self.sale_order.invoice_ids
        down_pay_amt = self.sale_order.amount_total / 2
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                       'balance',    'price_total'],
            # base lines
            [self.revenue_account.id,    (tax_10_incl + self.tax_10).ids, -90.91,       109.09       ],
            [self.revenue_account.id,    self.tax_10.ids,                 -200,         220          ],
            [self.revenue_account.id,    self.env['account.tax'],         -100,         100          ],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],         -29.09,       0            ],
            [self.tax_account.id,        self.env['account.tax'],         -9.09,        0            ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],         down_pay_amt, 0            ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_price_include_include_base_amount_breakdown(self):
        tax_10_pi_ba = self.create_tax(10, {'price_include_override': 'tax_included', 'include_base_amount': True})
        self.tax_10.sequence = 2
        self.sale_order.order_line[0].tax_ids = tax_10_pi_ba + self.tax_10
        self.sale_order.order_line[1].tax_ids = self.tax_10
        self.sale_order.order_line[2].tax_ids = self.tax_10
        self.make_downpayment()
        invoice = self.sale_order.invoice_ids
        down_pay_amt = self.sale_order.amount_total / 2
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                       'balance',     'price_total'],
            # base lines
            [self.revenue_account.id,    (tax_10_pi_ba + self.tax_10).ids, -90.91,       110          ],
            [self.revenue_account.id,    self.tax_10.ids,                  -200,         220          ],
            [self.revenue_account.id,    self.env['account.tax'],          -100,         100          ],
            # taxes
            [self.tax_account.id,        self.tax_10.ids,                  -9.09,        0            ],
            [self.tax_account.id,        self.env['account.tax'],          -30,          0            ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],          down_pay_amt, 0            ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_breakdown_with_discount(self):
        self.sale_order.order_line[0].tax_ids = self.tax_10
        self.sale_order.order_line[1].tax_ids = self.tax_10
        self.sale_order.order_line[1].discount = 25.0
        self.sale_order.order_line[2].tax_ids = self.tax_15
        self.make_downpayment()
        invoice = self.sale_order.invoice_ids
        down_pay_amt = self.sale_order.amount_total / 2
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',               'balance',    'price_total' ],
            # base lines
            [self.revenue_account.id,    self.tax_10.ids,         -175,         192.5         ],
            [self.revenue_account.id,    self.tax_15.ids,         -100,         115           ],
            [self.revenue_account.id,    self.env['account.tax'], -100,         100           ],
            # taxes
            [self.tax_account.id,        self.env['account.tax'], -17.5,        0             ],
            [self.tax_account.id,        self.env['account.tax'], -15,          0             ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'], down_pay_amt, 0             ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_price_include_include_base_amount_breakdown_with_discount(self):
        tax_10_pi_ba = self.create_tax(10, {'price_include_override': 'tax_included', 'include_base_amount': True})
        self.tax_10.sequence = 2
        self.sale_order.order_line[0].tax_ids = tax_10_pi_ba + self.tax_10
        self.sale_order.order_line[0].discount = 25.0
        self.sale_order.order_line[1].tax_ids = self.tax_10
        self.sale_order.order_line[2].tax_ids = self.tax_10
        self.make_downpayment()
        invoice = self.sale_order.invoice_ids
        down_pay_amt = self.sale_order.amount_total / 2
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                       'balance',     'price_total'],
            # base lines
            [self.revenue_account.id,    (tax_10_pi_ba + self.tax_10).ids, -68.18,       82.5         ],
            [self.revenue_account.id,    self.tax_10.ids,                  -200,         220          ],
            [self.revenue_account.id,    self.env['account.tax'],          -100,         100          ],
            # taxes
            [self.tax_account.id,        self.tax_10.ids,                  -6.82,        0            ],
            [self.tax_account.id,        self.env['account.tax'],          -27.5,        0            ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],          down_pay_amt, 0            ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_fixed_amount_breakdown(self):
        tax_10_fix_a = self.create_tax(10, {'amount_type': 'fixed', 'include_base_amount': True})
        tax_10_fix_b = self.create_tax(10, {'amount_type': 'fixed', 'include_base_amount': True})
        tax_10_fix_c = self.create_tax(10, {'amount_type': 'fixed'})
        tax_10_a = self.tax_10
        tax_10_b = self.create_tax(10)
        tax_group_1 = self.env['account.tax'].create({
            'name': "Tax Group",
            'amount_type': 'group',
            'children_tax_ids': [Command.set((tax_10_fix_a + tax_10_a + tax_10_fix_b + tax_10_b).ids)],
            'type_tax_use': 'sale',
        })
        tax_group_2 = self.env['account.tax'].create({
            'name': "Tax Group 2",
            'amount_type': 'group',
            'children_tax_ids': [Command.set((tax_10_fix_c + tax_10_a).ids)],
            'type_tax_use': 'sale',
        })
        self.sale_order.order_line[0].tax_ids = tax_group_1
        self.sale_order.order_line[1].tax_ids = tax_group_2
        self.sale_order.order_line[2].tax_ids = tax_10_a
        self.make_downpayment()

        # Line 1: 200 + 80 = 284
        # Line 2: 200 + 40 = 240
        # Line 3: 200 + 20 = 220
        # Line 4: 200
        # Total: 944

        invoice = self.sale_order.invoice_ids
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                 'balance',    'price_total'],
            # base lines
            [self.revenue_account.id,    (tax_10_a + tax_10_b).ids, -110,         132          ],
            [self.revenue_account.id,    tax_10_b.ids,              -10,          11           ],
            [self.revenue_account.id,    tax_10_a.ids,              -200,         220          ],
            [self.revenue_account.id,    self.env['account.tax'],   -110,         110          ],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],   -31,          0            ],
            [self.tax_account.id,        self.env['account.tax'],   -12,          0            ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],   473,          0            ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_fixed_amount_price_include(self):
        tax_fix = self.create_tax(5, {'amount_type': 'fixed', 'include_base_amount': True, 'price_include_override': 'tax_included'})
        tax_percentage = self.create_tax(21, {'amount_type': 'percent', 'price_include_override': 'tax_included'})
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'name': 'line1',
                    'product_id': self.company_data['product_order_no'].id,
                    'product_uom_qty': 1,
                    'price_unit': 1210,
                    'tax_ids': [Command.set((tax_fix + tax_percentage).ids)],
                }),
            ],
        })

        downpayment = self.env['sale.advance.payment.inv']\
            .with_context(active_ids=sale_order.ids, active_model=sale_order._name)\
            .create({
                'advance_payment_method': 'fixed',
                'fixed_amount': 200.0,
            })
        downpayment.create_invoices()
        sale_order.action_confirm()
        invoice = sale_order.invoice_ids

        self.assertRecordValues(invoice.invoice_line_ids, [{'price_unit': 200.0, 'tax_ids': tax_percentage.ids}])
        self.assertRecordValues(invoice.line_ids, [
            {'balance': -165.29},
            {'balance': -34.71},
            {'balance': 200},
        ])

    def test_analytic_distribution(self):
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test'})
        an_acc_01 = str(self.env['account.analytic.account'].create({'name': 'Account 01', 'plan_id': analytic_plan.id}).id)
        an_acc_02 = str(self.env['account.analytic.account'].create({'name': 'Account 02', 'plan_id': analytic_plan.id}).id)
        self.sale_order.order_line[0].tax_ids = self.tax_15 + self.tax_10
        self.sale_order.order_line[0].analytic_distribution = {an_acc_01: 100}
        self.sale_order.order_line[1].tax_ids = self.tax_10
        self.sale_order.order_line[1].analytic_distribution = {an_acc_01: 50, an_acc_02: 50}
        self.sale_order.order_line[2].tax_ids = self.tax_10
        self.sale_order.order_line[2].analytic_distribution = {an_acc_01: 100}
        self.make_downpayment()
        invoice = self.sale_order.invoice_ids
        down_pay_amt = self.sale_order.amount_total / 2
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                      'balance',     'price_total', 'analytic_distribution'       ],
            # base lines
            [self.revenue_account.id,    (self.tax_15 + self.tax_10).ids, -100,         125,           {an_acc_01: 100}              ],
            [self.revenue_account.id,    self.tax_10.ids,                 -200,         220,           {an_acc_01: 75, an_acc_02: 25}],
            [self.revenue_account.id,    self.env['account.tax'],         -100,         100 ,          False                         ],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],         -30,          0,             False                         ],
            [self.tax_account.id,        self.env['account.tax'],         -15,          0,             False                         ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],         down_pay_amt, 0,             False                         ],
        ]

        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_analytic_distribution_zero_line(self):
        # do not add 0 price_unit lines and do not create analytic distributions for them
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test'})
        an_acc_01 = str(self.env['account.analytic.account'].create({'name': 'Account 01', 'plan_id': analytic_plan.id}).id)
        an_acc_02 = str(self.env['account.analytic.account'].create({'name': 'Account 02', 'plan_id': analytic_plan.id}).id)
        self.sale_order.order_line[0].tax_ids = self.tax_15
        self.sale_order.order_line[0].analytic_distribution = {an_acc_01: 50, an_acc_02: 50}
        self.sale_order.order_line[1].tax_ids = self.tax_10
        self.sale_order.order_line[1].analytic_distribution = {an_acc_01: 50, an_acc_02: 50}
        self.sale_order.order_line[2].tax_ids = self.tax_10
        self.sale_order.order_line[2].analytic_distribution = {an_acc_01: 50, an_acc_02: 50}
        self.sale_order.order_line[2].price_unit = - self.sale_order.order_line[1].price_unit
        self.make_downpayment()
        invoice = self.sale_order.invoice_ids
        down_pay_amt = self.sale_order.amount_total / 2
        # ruff: noqa: E271, E272
        expected = [
            # keys
            ['account_id',               'tax_ids',               'balance',    'price_total', 'analytic_distribution'       ],
            # base lines
            [self.revenue_account.id,    self.tax_15.ids,         -100,         115,           {an_acc_01: 50, an_acc_02: 50}],
            [self.revenue_account.id,    self.env['account.tax'], -100,         100,           False                         ],
            # taxes
            [self.tax_account.id,        self.env['account.tax'], -15,          0,             False                         ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'], down_pay_amt, 0,             False                         ],
        ]

        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_fixed_amount_analytic_distribution(self):
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test'})
        an_acc_01 = str(self.env['account.analytic.account'].create({'name': 'Account 01', 'plan_id': analytic_plan.id}).id)
        an_acc_02 = str(self.env['account.analytic.account'].create({'name': 'Account 02', 'plan_id': analytic_plan.id}).id)
        tax_10_fix_a = self.create_tax(10, {'amount_type': 'fixed', 'include_base_amount': True})
        tax_10_fix_b = self.create_tax(10, {'amount_type': 'fixed', 'include_base_amount': True})
        tax_10_fix_c = self.create_tax(10, {'amount_type': 'fixed'})
        tax_10_a = self.tax_10
        tax_10_b = self.create_tax(10)
        tax_group_1 = self.env['account.tax'].create({
            'name': "Tax Group",
            'amount_type': 'group',
            'children_tax_ids': [Command.set((tax_10_fix_a + tax_10_a + tax_10_fix_b + tax_10_b).ids)],
            'type_tax_use': 'sale',
        })
        tax_group_2 = self.env['account.tax'].create({
            'name': "Tax Group 2",
            'amount_type': 'group',
            'children_tax_ids': [Command.set((tax_10_fix_c + tax_10_a).ids)],
            'type_tax_use': 'sale',
        })
        self.sale_order.order_line[0].tax_ids = tax_group_1
        self.sale_order.order_line[0].analytic_distribution = {an_acc_01: 50, an_acc_02: 50}
        self.sale_order.order_line[1].tax_ids = tax_group_2
        self.sale_order.order_line[2].tax_ids = tax_10_a

        # Line 1: 200 + 80 = 284
        # Line 2: 200 + 40 = 240
        # Line 3: 200 + 20 = 220
        # Line 4: 200
        # Total: 944

        self.make_downpayment()
        invoice = self.sale_order.invoice_ids
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                 'balance',    'price_total', 'analytic_distribution'],
            # base lines
            [self.revenue_account.id,    (tax_10_a + tax_10_b).ids, -110,         132,            {an_acc_01: 50, an_acc_02: 50}],
            [self.revenue_account.id,    tax_10_b.ids,              -10,          11,             {an_acc_01: 50, an_acc_02: 50}],
            [self.revenue_account.id,    tax_10_a.ids,              -200,         220,            False                         ],
            [self.revenue_account.id,    self.env['account.tax'],   -110,         110,            False                         ],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],   -31,          0,              False                         ],
            [self.tax_account.id,        self.env['account.tax'],   -12,          0,              False                         ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],   473,          0,              False                         ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_price_include_amount_rounding(self):
        """Test downpayment fixed amount is correctly reported in downpayment invoice product line
           and in original SO amount invoiced"""
        tax_21 = self.create_tax(21)

        self.sale_order.order_line[0].price_unit = 900
        self.sale_order.order_line[0].product_uom_qty = 1
        self.sale_order.order_line[0].tax_ids = tax_21

        self.sale_order.order_line[1].price_unit = 90
        self.sale_order.order_line[1].product_uom_qty = 2
        self.sale_order.order_line[1].tax_ids = tax_21

        self.sale_order.order_line[2].price_unit = 49
        self.sale_order.order_line[2].product_uom_qty = 4
        self.sale_order.order_line[2].tax_ids = tax_21

        self.sale_order.order_line[3].unlink()
        self.sale_order.action_confirm()

        so_context = {
            'active_model': 'sale.order',
            'active_ids': [self.sale_order.id],
            'active_id': self.sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }
        payment_params = {
            'advance_payment_method': 'fixed',
            'fixed_amount': 550.0,
        }
        downpayment = self.env['sale.advance.payment.inv'].with_context(so_context).create(payment_params)
        downpayment.create_invoices()
        invoice = self.sale_order.invoice_ids
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                       'balance',    'price_total'],
            # base lines
            [self.revenue_account.id,    tax_21.ids,                      -454.55,       550.0       ],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],         -95.45,        0           ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],         550.0,         0           ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)
        invoice.action_post()
        downpayment = self.env['sale.advance.payment.inv'].with_context(so_context).create(payment_params)
        self.assertEqual(downpayment.amount_invoiced, 550.0, "Amount invoiced is not equal to downpayment amount")

    def test_tax_price_include_negative_amount_rounding_final_invoice(self):
        """Test downpayment fixed amount rounding from downpayment to final invoice.
           Downpayment fixed amount is tax incl. This can lead to rounding problems, e.g. :
           Fixed amount = 100€, tax is 21%
           100 / 1.21 = 82.64, 82.64 * 1.21 = 99.99 -> 100€ does not correspond to any base amount + 21% tax."""
        tax_21_a = self.create_tax(21)
        tax_21_b = self.create_tax(21)

        self.sale_order.order_line[0].product_id = self.company_data['product_delivery_no'].id,
        self.sale_order.order_line[0].product_uom_qty = 1
        self.sale_order.order_line[0].qty_delivered = 0
        self.sale_order.order_line[0].tax_ids = tax_21_a
        self.sale_order.order_line[0].price_unit = 1000

        self.sale_order.order_line[1].product_id = self.company_data['product_delivery_no'].id,
        self.sale_order.order_line[1].product_uom_qty = 1
        self.sale_order.order_line[1].qty_delivered = 0
        self.sale_order.order_line[1].tax_ids = tax_21_b
        self.sale_order.order_line[1].price_unit = 1000

        self.sale_order.order_line[2:].unlink()

        self.sale_order.action_confirm()

        so_context = {
            'active_model': 'sale.order',
            'active_ids': [self.sale_order.id],
            'active_id': self.sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }
        payment_params = {
            'advance_payment_method': 'fixed',
            'fixed_amount': 200.0,
        }
        downpayment = self.env['sale.advance.payment.inv'].with_context(so_context).create(payment_params)
        action = downpayment.create_invoices()
        invoice = self.env['account.move'].browse(action['res_id'])
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',    'balance', 'price_total'],
            # base lines
            [self.revenue_account.id,    tax_21_a.ids, -82.64,     100.0       ],
            [self.revenue_account.id,    tax_21_b.ids, -82.64,     100.0       ],
            # taxes
            [self.tax_account.id,        [],           -17.36,     0.0         ],
            [self.tax_account.id,        [],           -17.36,     0.0         ],
            # receivable
            [self.receivable_account.id, [],           200.0,      0.0         ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)
        invoice.action_post()
        self.assertEqual(downpayment.amount_invoiced, 200.0, "Amount invoiced is not equal to downpayment amount")

        # final invoice which is a credit note as there ar no deliveries to invoice and there already is 200 paid
        payment_params = {
            'advance_payment_method': 'delivered',
        }
        downpayment = self.env['sale.advance.payment.inv'].with_context({**so_context, 'raise_if_nothing_to_invoice': False}).create(payment_params)
        action = downpayment.create_invoices()
        invoice = self.env['account.move'].browse(action['res_id'])
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',    'balance', 'price_total'],
            # line section
            [False,                      [],           0.0,       0.0          ],
            # down payment
            [self.revenue_account.id,    tax_21_a.ids, 82.64,     100.0        ],
            [self.revenue_account.id,    tax_21_b.ids, 82.64,     100.0        ],
            # receivable
            [self.receivable_account.id, [],           -200,      0.0          ],
            # taxes
            [self.tax_account.id,        [],           17.36,     0.0          ],
            [self.tax_account.id,        [],           17.36,     0.0          ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)
        self.assertEqual(downpayment.amount_invoiced, 200.0, "Amount invoiced is not equal to downpayment amount")

        # final invoice with all products delivered
        invoice.unlink()
        self.sale_order.order_line[0].qty_delivered = 1
        self.sale_order.order_line[1].qty_delivered = 1
        downpayment = self.env['sale.advance.payment.inv'].with_context(so_context).create(payment_params)
        action = downpayment.create_invoices()
        invoice = self.env['account.move'].browse(action['res_id'])
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',    'balance', 'price_total'],
            # base lines
            [self.revenue_account.id,    tax_21_a.ids, -1000.0,   1210.0       ],
            [self.revenue_account.id,    tax_21_b.ids, -1000.0,   1210.0       ],
            # line section
            [False,                      [],           0.0,       0.0          ],
            # down payment
            [self.revenue_account.id,    tax_21_a.ids, 82.64,     -100.0       ],
            [self.revenue_account.id,    tax_21_b.ids, 82.64,     -100.0       ],
            # taxes
            [self.tax_account.id,        [],           -192.64,   0.0          ],
            [self.tax_account.id,        [],           -192.64,   0.0          ],
            # receivable
            [self.receivable_account.id, [],           2220.0,    0.0          ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_price_include_positive_amount_rounding_final_invoice(self):
        """Test downpayment fixed amount rounding from downpayment to final invoice.
           Downpayment fixed amount is tax incl. This can lead to rounding problems, e.g. :
           Fixed amount = 100€, tax is 24%
           100 / 1.24 = 80.65, 80.65 * 1.24 = 100,01 -> 100€ does not correspond to any base amount + 24% tax."""
        tax_24_a = self.create_tax(24)
        tax_24_b = self.create_tax(24)

        self.sale_order.order_line[0].product_id = self.company_data['product_delivery_no'].id,
        self.sale_order.order_line[0].product_uom_qty = 1
        self.sale_order.order_line[0].qty_delivered = 0
        self.sale_order.order_line[0].tax_ids = tax_24_a
        self.sale_order.order_line[0].price_unit = 1000

        self.sale_order.order_line[1].product_id = self.company_data['product_delivery_no'].id,
        self.sale_order.order_line[1].product_uom_qty = 1
        self.sale_order.order_line[1].qty_delivered = 0
        self.sale_order.order_line[1].tax_ids = tax_24_b
        self.sale_order.order_line[1].price_unit = 1000

        self.sale_order.order_line[2:].unlink()

        self.sale_order.action_confirm()

        so_context = {
            'active_model': 'sale.order',
            'active_ids': [self.sale_order.id],
            'active_id': self.sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }
        payment_params = {
            'advance_payment_method': 'fixed',
            'fixed_amount': 200.0,
        }
        downpayment = self.env['sale.advance.payment.inv'].with_context(so_context).create(payment_params)
        action = downpayment.create_invoices()
        invoice = self.env['account.move'].browse(action['res_id'])
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',    'balance', 'price_total'],
            # base lines
            [self.revenue_account.id,    tax_24_a.ids, -80.65,     100.0       ],
            [self.revenue_account.id,    tax_24_b.ids, -80.65,     100.0       ],
            # taxes
            [self.tax_account.id,        [],           -19.35,     0.0         ],
            [self.tax_account.id,        [],           -19.35,     0.0         ],
            # receivable
            [self.receivable_account.id, [],           200.0,      0.0         ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)
        invoice.action_post()
        self.assertEqual(downpayment.amount_invoiced, 200.0, "Amount invoiced is not equal to downpayment amount")

        # final invoice which is a credit note as there ar no deliveries to invoice and there already is 200 paid
        payment_params = {'advance_payment_method': 'delivered'}
        downpayment = self.env['sale.advance.payment.inv'].with_context({**so_context, 'raise_if_nothing_to_invoice': False}).create(payment_params)
        action = downpayment.create_invoices()
        invoice = self.env['account.move'].browse(action['res_id'])
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',    'balance', 'price_total'],
            # line section
            [False,                      [],           0.0,       0.0          ],
            # down payment
            [self.revenue_account.id,    tax_24_a.ids, 80.65,     100.0        ],
            [self.revenue_account.id,    tax_24_b.ids, 80.65,     100.0        ],
            # receivable
            [self.receivable_account.id, [],           -200,      0.0          ],
            # taxes
            [self.tax_account.id,        [],           19.35,     0.0          ],
            [self.tax_account.id,        [],           19.35,     0.0          ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)
        self.assertEqual(downpayment.amount_invoiced, 200.0, "Amount invoiced is not equal to downpayment amount")

        # final invoice with all products delivered
        invoice.unlink()
        self.sale_order.order_line[0].qty_delivered = 1
        self.sale_order.order_line[1].qty_delivered = 1
        downpayment = self.env['sale.advance.payment.inv'].with_context(so_context).create(payment_params)
        action = downpayment.create_invoices()
        invoice = self.env['account.move'].browse(action['res_id'])
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',              'tax_ids',     'balance', 'price_total'],
            # base lines
            [self.revenue_account.id,    tax_24_a.ids, -1000.0,   1240.0       ],
            [self.revenue_account.id,    tax_24_b.ids, -1000.0,   1240.0       ],
            # line section
            [False,                      [],            0.0,      0.0          ],
            # down payment
            [self.revenue_account.id,    tax_24_a.ids,  80.65,    -100.0       ],
            [self.revenue_account.id,    tax_24_b.ids,  80.65,    -100.0       ],
            # taxes
            [self.tax_account.id,        [],            -220.65,  0.0          ],
            [self.tax_account.id,        [],            -220.65,  0.0          ],
            # receivable
            [self.receivable_account.id, [],            2280.0,   0.0          ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)


    def test_tax_price_include_small_amount_rounding_final_invoice(self):
        """Test downpayment fixed amount rounding from downpayment to final invoice.
           Downpayment fixed amount is tax incl. This can lead to rounding problems.
           Check that if the rounding error is to small (less than currency rounding)
           to ventilate on each line, it is sill added/removed on one/some lines.
           """
        tax_21_a = self.create_tax(21)
        tax_21_b = self.create_tax(21)
        tax_25_a = self.create_tax(25)
        tax_25_b = self.create_tax(25)
        tax_25_c = self.create_tax(25)

        self.sale_order.order_line[0].product_id = self.company_data['product_delivery_no'].id,
        self.sale_order.order_line[0].product_uom_qty = 1
        self.sale_order.order_line[0].qty_delivered = 1
        self.sale_order.order_line[0].tax_ids = tax_21_a
        self.sale_order.order_line[0].price_unit = 1000

        self.sale_order.order_line[1].product_id = self.company_data['product_delivery_no'].id,
        self.sale_order.order_line[1].product_uom_qty = 1
        self.sale_order.order_line[1].qty_delivered = 1
        self.sale_order.order_line[1].tax_ids = tax_21_b
        self.sale_order.order_line[1].price_unit = 1000

        self.sale_order.order_line[2].product_id = self.company_data['product_delivery_no'].id,
        self.sale_order.order_line[2].product_uom_qty = 1
        self.sale_order.order_line[2].qty_delivered = 1
        self.sale_order.order_line[2].tax_ids = tax_25_a
        self.sale_order.order_line[2].price_unit = 968

        self.sale_order.order_line[3].product_id = self.company_data['product_delivery_no'].id,
        self.sale_order.order_line[3].product_uom_qty = 1
        self.sale_order.order_line[3].qty_delivered = 1
        self.sale_order.order_line[3].tax_ids = tax_25_b
        self.sale_order.order_line[3].price_unit = 968

        self.sale_order.order_line[3].copy({
            'order_id':self.sale_order.id,
            'tax_ids': tax_25_c,
            'qty_delivered': 1,
        })

        self.sale_order.order_line.qty_delivered_method = 'manual'

        self.sale_order.action_confirm()

        so_context = {
            'active_model': 'sale.order',
            'active_ids': [self.sale_order.id],
            'active_id': self.sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }
        payment_params = {
            'advance_payment_method': 'fixed',
            'fixed_amount': 500.0,
        }
        downpayment = self.env['sale.advance.payment.inv'].with_context(so_context).create(payment_params)
        action = downpayment.create_invoices()
        invoice = self.env['account.move'].browse(action['res_id'])
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',              'tax_ids',    'balance', 'price_total'],
            # base lines
            [self.revenue_account.id,    tax_21_a.ids, -82.64,     100.0       ],
            [self.revenue_account.id,    tax_21_b.ids, -82.64,     100.0       ],
            [self.revenue_account.id,    tax_25_a.ids, -80.0,      100.0       ],
            [self.revenue_account.id,    tax_25_b.ids, -80.0,      100.0       ],
            [self.revenue_account.id,    tax_25_c.ids, -80.0,      100.0       ],
            # taxes
            [self.tax_account.id,        [],           -17.36,     0.0         ],
            [self.tax_account.id,        [],           -17.36,     0.0         ],
            [self.tax_account.id,        [],           -20.0,      0.0         ],
            [self.tax_account.id,        [],           -20.0,      0.0         ],
            [self.tax_account.id,        [],           -20.0,      0.0         ],
            # receivable
            [self.receivable_account.id, [],           500.0,      0.0         ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)
        invoice.action_post()
        downpayment = self.env['sale.advance.payment.inv'].with_context(so_context).create(payment_params)
        self.assertEqual(downpayment.amount_invoiced, 500.0, "Amount invoiced is not equal to downpayment amount")
        # final invoice
        payment_params = {'advance_payment_method': 'delivered'}
        downpayment = self.env['sale.advance.payment.inv'].with_context(so_context).create(payment_params)
        action = downpayment.create_invoices()
        invoice = self.env['account.move'].browse(action['res_id'])
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',              'tax_ids',     'balance', 'price_total'],
            # base lines
            [self.revenue_account.id,   tax_21_a.ids,  -1000.0,   1210.0       ],
            [self.revenue_account.id,   tax_21_b.ids,  -1000.0,   1210.0       ],
            [self.revenue_account.id,   tax_25_a.ids,  -968.0,    1210.0       ],
            [self.revenue_account.id,   tax_25_b.ids,  -968.0,    1210.0       ],
            [self.revenue_account.id,   tax_25_c.ids,  -968.0,    1210.0       ],
            # line section
            [False,                     [],            0.0,       0.0          ],
            # down payment
            [self.revenue_account.id,    tax_21_a.ids, 82.64,    -100.0       ],
            [self.revenue_account.id,    tax_21_b.ids, 82.64,    -100.0       ],
            [self.revenue_account.id,    tax_25_a.ids, 80.0,     -100.0       ],
            [self.revenue_account.id,    tax_25_b.ids, 80.0,     -100.0       ],
            [self.revenue_account.id,    tax_25_c.ids, 80.0,     -100.0       ],
            # taxes
            [self.tax_account.id,        [],           -192.64,  0.0          ],
            [self.tax_account.id,        [],           -192.64,  0.0          ],
            [self.tax_account.id,        [],           -222.0,   0.0          ],
            [self.tax_account.id,        [],           -222.0,   0.0          ],
            [self.tax_account.id,        [],           -222.0,   0.0          ],
            # receivable
            [self.receivable_account.id, [],           5550.0,   0.0          ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_so_with_multiple_line_rounding(self):
        """Test downpayment fixed amount rounding when the sale order has
           multiple lines that would create a sensible difference in rounding.
        """
        tax_20 = self.create_tax(20)

        for i, price_unit in enumerate((10000, 10000, 10000, 50)):
            self.sale_order.order_line[i].product_id = self.company_data['product_delivery_no'].id
            self.sale_order.order_line[i].product_uom_qty = 1
            self.sale_order.order_line[i].qty_delivered = 1
            self.sale_order.order_line[i].tax_ids = tax_20
            self.sale_order.order_line[i].price_unit = price_unit

        self.sale_order.order_line.qty_delivered_method = 'manual'
        self.sale_order.action_confirm()

        so_context = {
            'active_model': 'sale.order',
            'active_ids': [self.sale_order.id],
            'active_id': self.sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }
        payment_params = {
            'advance_payment_method': 'fixed',
            'fixed_amount': 840.0,  # with 20% tax applied, amount tax excluded is 700.0
        }
        downpayment = self.env['sale.advance.payment.inv'].with_context(so_context).create(payment_params)
        action = downpayment.create_invoices()
        invoice = self.env['account.move'].browse(action['res_id'])
        expected = [
            # keys
            ['account_id',              'tax_ids',   'balance', 'price_total'],
            # base lines
            [self.revenue_account.id,    tax_20.ids, -700,      840.0],
            # taxes
            [self.tax_account.id,        [],         -140,      0.0],
            # receivable
            [self.receivable_account.id, [],         840.0,     0.0],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_so_downpayment_invoice_credited_reinvoiced(self):
        """
        Test that, after a downpayment, if the rest has been invoiced, credited and re-invoiced
        The amount of the downpayment is subtracted (not added)
        """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
        })
        # the tax is needed
        self.env['sale.order.line'].create({
            'name': self.company_data['product_order_no'].name,
            'product_id': self.company_data['product_order_no'].id,
            'product_uom_qty': 1,
            'price_unit': 100,
            'tax_ids': self.tax_15.ids,
            'order_id': sale_order.id,
        })
        sale_order.action_confirm()

        so_context = {
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }
        payment_params = {
            'advance_payment_method': 'fixed',
            'fixed_amount': 50.0,
        }
        downpayment = self.env['sale.advance.payment.inv'].with_context(so_context).create(payment_params)
        action = downpayment.create_invoices()
        downpayment_invoice = self.env['account.move'].browse(action['res_id'])
        downpayment_invoice.action_post()

        payment_params = {
            'advance_payment_method': 'delivered',
        }

        invoice_to_be_refund = self.env['sale.advance.payment.inv'].with_context(so_context).create(payment_params)
        action = invoice_to_be_refund.create_invoices()
        invoice_to_be_refund = self.env['account.move'].browse(action['res_id'])
        invoice_to_be_refund.action_post()

        credit_note_wizard = self.env['account.move.reversal'].with_context(
            {'active_ids': [invoice_to_be_refund.id], 'active_id': invoice_to_be_refund.id,
             'active_model': 'account.move'}).create({
            'reason': 'reason test create',
            'journal_id': invoice_to_be_refund.journal_id.id,
        })
        action = credit_note_wizard.reverse_moves()
        credit_note = self.env['account.move'].browse(action['res_id'])
        credit_note.action_post()

        final_invoice = self.env['sale.advance.payment.inv'].with_context(so_context).create(payment_params)
        action = final_invoice.create_invoices()
        final_invoice = self.env['account.move'].browse(action['res_id'])

        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',              'tax_ids',          'balance',          'price_total'],
            # base lines
            [self.revenue_account.id,   self.tax_15.ids,    -100.0,             115.0],
            # line section
            [False,                     [],                 0.0,                0.0],
            # down payment
            [self.revenue_account.id,   self.tax_15.ids,    43.48,              -50.0],
            # taxes
            [self.tax_account.id,       [],                 -8.48,              0.0],
            # receivable
            [self.receivable_account.id, [],                 65.0,               0.0],
        ]

        self._assert_invoice_lines_values(final_invoice.line_ids, expected)

    def test_downpayment_description(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.company_data['product_order_no'].id,
                })
            ]
        })
        sale_order.action_confirm()
        invoicing_wizard = self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'fixed',
            'fixed_amount': sale_order.amount_total / 2.0,
            'sale_order_ids': [Command.link(sale_order.id)],
        })

        # Down payment invoice
        action = invoicing_wizard.create_invoices()
        so_dp_line = sale_order.order_line.filtered(
            lambda sol: sol.is_downpayment and not sol.display_type)
        self.assertTrue(so_dp_line)
        self.assertIn('Draft', so_dp_line.name)
        dp_invoice = self.env['account.move'].browse(action['res_id'])
        self.assertEqual(dp_invoice.move_type, 'out_invoice')
        dp_invoice.action_post()
        self.assertIn('ref', so_dp_line.name)

        # Full Invoice
        invoicing_wizard = self.env['sale.advance.payment.inv'].create({
            'sale_order_ids': [Command.link(sale_order.id)],
            'advance_payment_method': 'delivered',
        })
        self.assertEqual(sale_order.invoice_status, 'to invoice')
        action = invoicing_wizard.create_invoices()
        full_invoice = self.env['account.move'].browse(action['res_id'])
        self.assertEqual(full_invoice.move_type, 'out_invoice')
        full_invoice.action_post()
        self.assertIn('ref', so_dp_line.name)

        # Credit Note
        action = dp_invoice.action_reverse()
        reversal_wizard = self.env[action['res_model']].with_context(
            active_ids=dp_invoice.ids,
            active_model='account.move',
        ).create({
            'journal_id': dp_invoice.journal_id.id,  # Field is not precompute but required
        })
        action = reversal_wizard.reverse_moves()
        reversal_move = self.env['account.move'].browse(action['res_id'])
        reversal_move.action_post()
        self.assertEqual(reversal_move.move_type, 'out_refund')
        self.assertIn('ref', so_dp_line.name)
