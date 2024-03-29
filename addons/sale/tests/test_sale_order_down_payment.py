import uuid

from odoo.tests import tagged
from odoo import Command
from .common import TestSaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrderDownPayment(TestSaleCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        SaleOrder = cls.env['sale.order'].with_context(tracking_disable=True)

        cls.tax_account = cls.env['account.account'].search([('account_type', '=', 'liability_current')], limit=1)
        cls.tax_10 = cls.create_tax(10)
        cls.tax_15 = cls.create_tax(15)

        # create a generic Sale Order with all classical products and empty pricelist
        cls.sale_order = SaleOrder.create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
        })
        cls.sol_product_order = cls.env['sale.order.line'].create({
            'name': cls.company_data['product_order_no'].name,
            'product_id': cls.company_data['product_order_no'].id,
            'product_uom_qty': 2,
            'product_uom': cls.company_data['product_order_no'].uom_id.id,
            'price_unit': 100,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_deliver = cls.env['sale.order.line'].create({
            'name': cls.company_data['product_service_delivery'].name,
            'product_id': cls.company_data['product_service_delivery'].id,
            'product_uom_qty': 2,
            'product_uom': cls.company_data['product_service_delivery'].uom_id.id,
            'price_unit': 100,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_order = cls.env['sale.order.line'].create({
            'name': cls.company_data['product_service_order'].name,
            'product_id': cls.company_data['product_service_order'].id,
            'product_uom_qty': 2,
            'product_uom': cls.company_data['product_service_order'].uom_id.id,
            'price_unit': 100,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_product_deliver = cls.env['sale.order.line'].create({
            'name': cls.company_data['product_delivery_no'].name,
            'product_id': cls.company_data['product_delivery_no'].id,
            'product_uom_qty': 2,
            'product_uom': cls.company_data['product_delivery_no'].uom_id.id,
            'price_unit': 100,
            'order_id': cls.sale_order.id,
            'tax_id': False,
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
            'deposit_account_id': cls.revenue_account.id,
            **kwargs,
        }
        downpayment = cls.env['sale.advance.payment.inv'].with_context(so_context).create(payment_params)
        downpayment.create_invoices()
        cls.sale_order.action_confirm()

    def _assert_invoice_lines_values(self, lines, expected):
        return self.assertRecordValues(lines, [dict(zip(expected[0], x)) for x in expected[1:]])

    def test_tax_breakdown(self):
        self.sale_order.order_line[0].tax_id = self.tax_15 + self.tax_10
        self.sale_order.order_line[1].tax_id = self.tax_10
        self.sale_order.order_line[2].tax_id = self.tax_10
        self.make_downpayment()
        invoice = self.sale_order.invoice_ids
        down_pay_amt = self.sale_order.amount_total / 2
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                      'balance',     'price_total'],
            # base lines
            [self.revenue_account.id,    (self.tax_15 + self.tax_10).ids, -100,         125          ],
            [self.revenue_account.id,    self.tax_10.ids,                 -200,         220          ],
            [self.revenue_account.id,    self.env['account.tax'],         -100,         100          ],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],         -30,          0            ],
            [self.tax_account.id,        self.env['account.tax'],         -15,          0            ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],         down_pay_amt, 0            ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_breakdown_other_currency(self):
        self.sale_order.currency_id = self.currency_data['currency']  # rate = 2.0
        self.sale_order.order_line[0].tax_id = self.tax_15 + self.tax_10
        self.sale_order.order_line[1].tax_id = self.tax_10
        self.sale_order.order_line[2].tax_id = self.tax_10
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
        self.sale_order.order_line[0].tax_id = self.tax_15 + self.tax_10
        self.sale_order.order_line[1].tax_id = self.tax_10
        self.sale_order.order_line[2].tax_id = self.tax_10
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
        self.sale_order.order_line[0].tax_id = self.tax_15
        self.sale_order.order_line[1].tax_id = self.tax_10
        self.sale_order.order_line[2].tax_id = self.tax_10
        self.sale_order.order_line[3].tax_id = self.tax_10
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
        tax_10_incl = self.create_tax(10, {'price_include': True})
        self.sale_order.order_line[0].tax_id = tax_10_incl + self.tax_10
        self.sale_order.order_line[1].tax_id = self.tax_10
        self.sale_order.order_line[2].tax_id = self.tax_10
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
        tax_10_pi_ba = self.create_tax(10, {'price_include': True, 'include_base_amount': True})
        self.tax_10.sequence = 2
        self.sale_order.order_line[0].tax_id = tax_10_pi_ba + self.tax_10
        self.sale_order.order_line[1].tax_id = self.tax_10
        self.sale_order.order_line[2].tax_id = self.tax_10
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
        self.sale_order.order_line[0].tax_id = self.tax_10
        self.sale_order.order_line[1].tax_id = self.tax_10
        self.sale_order.order_line[1].discount = 25.0
        self.sale_order.order_line[2].tax_id = self.tax_15
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
        tax_10_pi_ba = self.create_tax(10, {'price_include': True, 'include_base_amount': True})
        self.tax_10.sequence = 2
        self.sale_order.order_line[0].tax_id = tax_10_pi_ba + self.tax_10
        self.sale_order.order_line[0].discount = 25.0
        self.sale_order.order_line[1].tax_id = self.tax_10
        self.sale_order.order_line[2].tax_id = self.tax_10
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
        tax_10_a = self.tax_10.copy()
        tax_10_fix_b = self.create_tax(10, {'amount_type': 'fixed', 'include_base_amount': True})
        tax_10_fix_c = self.create_tax(10, {'amount_type': 'fixed'})
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
        self.sale_order.order_line[0].tax_id = tax_group_1
        self.sale_order.order_line[1].tax_id = tax_group_2
        self.sale_order.order_line[2].tax_id = tax_10_a

        # Line 1: 200 + 84 = 284
        # Line 2: 200 + 40 = 240
        # Line 3: 200 + 20 = 220
        # Line 4: 200
        # Total: 944

        self.make_downpayment()
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

    def test_analytic_distribution(self):
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test'})
        an_acc_01 = str(self.env['account.analytic.account'].create({'name': 'Account 01', 'plan_id': analytic_plan.id}).id)
        an_acc_02 = str(self.env['account.analytic.account'].create({'name': 'Account 02', 'plan_id': analytic_plan.id}).id)
        self.sale_order.order_line[0].tax_id = self.tax_15 + self.tax_10
        self.sale_order.order_line[0].analytic_distribution = {an_acc_01: 100}
        self.sale_order.order_line[1].tax_id = self.tax_10
        self.sale_order.order_line[1].analytic_distribution = {an_acc_01: 50, an_acc_02: 50}
        self.sale_order.order_line[2].tax_id = self.tax_10
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
            [self.revenue_account.id,    self.tax_10.ids,                 -100,         110,           {an_acc_01: 50, an_acc_02: 50}],
            [self.revenue_account.id,    self.tax_10.ids,                 -100,         110,           {an_acc_01: 100}],
            [self.revenue_account.id,    self.env['account.tax'],         -100,         100 ,          False                         ],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],         -30,          0,             False                         ],
            [self.tax_account.id,        self.env['account.tax'],         -15,          0,             False                         ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],         down_pay_amt, 0,             False                         ],
        ]

        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_fixed_amount_analytic_distribution(self):
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test'})
        an_acc_01 = str(self.env['account.analytic.account'].create({'name': 'Account 01', 'plan_id': analytic_plan.id}).id)
        an_acc_02 = str(self.env['account.analytic.account'].create({'name': 'Account 02', 'plan_id': analytic_plan.id}).id)
        tax_10_fix_a = self.create_tax(10, {'amount_type': 'fixed', 'include_base_amount': True})
        tax_10_a = self.tax_10.copy()
        tax_10_fix_b = self.create_tax(10, {'amount_type': 'fixed', 'include_base_amount': True})
        tax_10_fix_c = self.create_tax(10, {'amount_type': 'fixed'})
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
        self.sale_order.order_line[0].tax_id = tax_group_1
        self.sale_order.order_line[0].analytic_distribution = {an_acc_01: 50, an_acc_02: 50}
        self.sale_order.order_line[1].tax_id = tax_group_2
        self.sale_order.order_line[2].tax_id = tax_10_a

        # Line 1: 200 + 84 = 284
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
        self.sale_order.order_line[0].tax_id = tax_21

        self.sale_order.order_line[1].price_unit = 90
        self.sale_order.order_line[1].product_uom_qty = 2
        self.sale_order.order_line[1].tax_id = tax_21

        self.sale_order.order_line[2].price_unit = 49
        self.sale_order.order_line[2].product_uom_qty = 4
        self.sale_order.order_line[2].tax_id = tax_21

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
            'deposit_account_id': self.revenue_account.id,
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
        self.sale_order.order_line[0].tax_id = tax_21_a
        self.sale_order.order_line[0].price_unit = 1000

        self.sale_order.order_line[1].product_id = self.company_data['product_delivery_no'].id,
        self.sale_order.order_line[1].product_uom_qty = 1
        self.sale_order.order_line[1].qty_delivered = 0
        self.sale_order.order_line[1].tax_id = tax_21_b
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
            'deposit_account_id': self.revenue_account.id,
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
            'deposit_account_id': self.revenue_account.id,
        }
        downpayment = self.env['sale.advance.payment.inv'].with_context({**so_context, 'raise_if_nothing_to_invoice': False}).create(payment_params)
        action = downpayment.create_invoices()
        invoice = self.env['account.move'].browse(action['res_id'])
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',    'balance', 'price_total'],
            # line section
            [[],                         [],           0.0,       0.0          ],
            # down payment
            [self.revenue_account.id,    tax_21_a.ids, 82.64,     100.0        ],
            [self.revenue_account.id,    tax_21_b.ids, 82.64,     100.0        ],
            # taxes
            [self.tax_account.id,        [],           17.36,     0.0          ],
            [self.tax_account.id,        [],           17.36,     0.0          ],
            # receivable
            [self.receivable_account.id, [],           -200,      0.0          ],
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
            [[],                         [],           0.0,       0.0          ],
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
        self.sale_order.order_line[0].tax_id = tax_24_a
        self.sale_order.order_line[0].price_unit = 1000

        self.sale_order.order_line[1].product_id = self.company_data['product_delivery_no'].id,
        self.sale_order.order_line[1].product_uom_qty = 1
        self.sale_order.order_line[1].qty_delivered = 0
        self.sale_order.order_line[1].tax_id = tax_24_b
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
            'deposit_account_id': self.revenue_account.id,
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
        payment_params = {
            'advance_payment_method': 'delivered',
            'deposit_account_id': self.revenue_account.id,
        }
        downpayment = self.env['sale.advance.payment.inv'].with_context({**so_context, 'raise_if_nothing_to_invoice': False}).create(payment_params)
        action = downpayment.create_invoices()
        invoice = self.env['account.move'].browse(action['res_id'])
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',    'balance', 'price_total'],
            # line section
            [[],                         [],           0.0,       0.0          ],
            # down payment
            [self.revenue_account.id,    tax_24_a.ids, 80.65,     100.0        ],
            [self.revenue_account.id,    tax_24_b.ids, 80.65,     100.0        ],
            # taxes
            [self.tax_account.id,        [],           19.35,     0.0          ],
            [self.tax_account.id,        [],           19.35,     0.0          ],
            # receivable
            [self.receivable_account.id, [],           -200,      0.0          ],
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
            [[],                         [],            0.0,      0.0          ],
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
        self.sale_order.order_line[0].tax_id = tax_21_a
        self.sale_order.order_line[0].price_unit = 1000

        self.sale_order.order_line[1].product_id = self.company_data['product_delivery_no'].id,
        self.sale_order.order_line[1].product_uom_qty = 1
        self.sale_order.order_line[1].qty_delivered = 1
        self.sale_order.order_line[1].tax_id = tax_21_b
        self.sale_order.order_line[1].price_unit = 1000

        self.sale_order.order_line[2].product_id = self.company_data['product_delivery_no'].id,
        self.sale_order.order_line[2].product_uom_qty = 1
        self.sale_order.order_line[2].qty_delivered = 1
        self.sale_order.order_line[2].tax_id = tax_25_a
        self.sale_order.order_line[2].price_unit = 968

        self.sale_order.order_line[3].product_id = self.company_data['product_delivery_no'].id,
        self.sale_order.order_line[3].product_uom_qty = 1
        self.sale_order.order_line[3].qty_delivered = 1
        self.sale_order.order_line[3].tax_id = tax_25_b
        self.sale_order.order_line[3].price_unit = 968

        self.sale_order.order_line[3].copy({
            'order_id':self.sale_order.id,
            'tax_id': tax_25_c,
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
            'deposit_account_id': self.revenue_account.id,
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
        payment_params = {
            'advance_payment_method': 'delivered',
            'deposit_account_id': self.revenue_account.id,
        }
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
            [[],                        [],            0.0,       0.0          ],
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
