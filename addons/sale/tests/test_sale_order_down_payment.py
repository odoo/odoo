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
            'name': 'Tax %s' % amount,
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
        self.sale_order.order_line[0].tax_id = tax_group_1
        self.sale_order.order_line[1].tax_id = tax_group_2
        self.sale_order.order_line[2].tax_id = tax_10_a
        self.make_downpayment()
        invoice = self.sale_order.invoice_ids
        down_pay_amt = self.sale_order.amount_total / 2
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
            [self.receivable_account.id, self.env['account.tax'],   down_pay_amt, 0            ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_analytic_distribution(self):
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test', 'company_id': False})
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
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test', 'company_id': False})
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
        self.sale_order.order_line[0].tax_id = tax_group_1
        self.sale_order.order_line[0].analytic_distribution = {an_acc_01: 50, an_acc_02: 50}
        self.sale_order.order_line[1].tax_id = tax_group_2
        self.sale_order.order_line[2].tax_id = tax_10_a
        self.make_downpayment()
        invoice = self.sale_order.invoice_ids
        down_pay_amt = self.sale_order.amount_total / 2
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
            [self.receivable_account.id, self.env['account.tax'],   down_pay_amt, 0,              False                         ],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_warning_on_invoice_with_credit_limit(self):
        # Activate the Credit Limit feature and set a value for partner_a.
        self.env.company.account_use_credit_limit = True
        self.partner_a.credit_limit = 1000.0

        # Create and confirm a SO to reach (but not exceed) partner_a's credit limit.
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'order_line': [Command.create({
                'name': self.company_data['product_order_no'].name,
                'product_id': self.company_data['product_order_no'].id,
                'product_uom_qty': 1,
                'product_uom': self.company_data['product_order_no'].uom_id.id,
                'price_unit': 1000.0,
                'tax_id': False,
            })]
        })

        # Check that partner_a's credit is 0.0.
        self.assertEqual(self.partner_a.credit, 0.0)

        # Make sure partner_a's credit includes the newly confirmed SO.
        sale_order.action_confirm()
        self.partner_a.invalidate_recordset(['credit'])
        self.assertEqual(self.partner_a.credit, 1000.0)

        # Create a 50% down payment invoice.
        self.env['sale.advance.payment.inv'].with_context({
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }).create({
            'advance_payment_method': 'percentage',
            'amount': 50,
            'deposit_account_id': self.revenue_account.id,
        }).create_invoices()

        invoice = sale_order.invoice_ids

        # Check that the warning does not appear even though we are creating an invoice
        # that should bring partner_a's credit above its limit.
        self.assertEqual(invoice.partner_credit_warning, '')


        # Make the down payment invoice amount larger than the Amount to Invoice
        # and check that the warning appears with the correct amounts,
        # i.e. 1.500 instead of 2.500 (1.000 SO + 1.500 down payment invoice).
        invoice.invoice_line_ids.quantity = 3
        self.assertEqual(
            invoice.partner_credit_warning,
            "partner_a has reached its Credit Limit of : $\xa01,000.00\n"
            "Total amount due (including this document) : $\xa01,500.00"
        )

        invoice.invoice_line_ids.quantity = 1
        invoice.action_post()

        # Create a credit note reversing the invoice
        self.env['account.move.reversal'].with_company(self.env.company).create(
            {
                'move_ids': [Command.set((invoice.id,))],
                'date_mode': 'custom',
                'journal_id': invoice.journal_id.id
            }
        ).reverse_moves()

        credit_note = sale_order.invoice_ids[1]
        credit_note.action_post()

        # Check that the credit note is accounted for correctly for the amount_to_invoice
        self.assertEqual(sale_order.amount_to_invoice, sale_order.amount_total)
