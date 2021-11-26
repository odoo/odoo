from odoo.tests import tagged

from .common import TestSaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrderDownPayment(TestSaleCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        SaleOrder = cls.env['sale.order'].with_context(tracking_disable=True)

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

        cls.account_revenue = cls.company_data['default_account_revenue']
        cls.receivable_account = cls.company_data['default_account_receivable']

    @classmethod
    def create_tax(cls, amount, values=None):
        vals = {
            'name': 'Tax %s' % amount,
            'amount_type': 'percent',
            'amount': amount,
            'type_tax_use': 'sale',
        }
        if values:
            vals.update(values)
        return cls.env['account.tax'].create(vals)

    def make_downpayment(self, **kwargs):
        so_context = {
            'active_model': 'sale.order',
            'active_ids': [self.sale_order.id],
            'active_id': self.sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }
        payment_params = {
            'advance_payment_method': 'percentage',
            'amount': 50,
            'deposit_account_id': self.account_revenue.id
        }
        payment_params.update(kwargs)
        downpayment = self.env['sale.advance.payment.inv'].with_context(so_context).create(payment_params)
        downpayment.create_invoices()
        self.sale_order.action_confirm()

    def test_tax_brakedown(self):
        self.sale_order.order_line[0].tax_id = self.tax_15 + self.tax_10
        self.sale_order.order_line[1].tax_id = self.tax_10
        self.sale_order.order_line[2].tax_id = self.tax_10
        self.make_downpayment()
        invoice = self.sale_order.invoice_ids
        down_pay_amt = self.sale_order.amount_total / 2
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                      'price_subtotal', 'price_total'  ],
            # base lines
            [self.account_revenue.id,    (self.tax_15 + self.tax_10).ids, 100,               125          ],
            [self.account_revenue.id,    self.tax_10.ids,                 200,               220          ],
            [self.account_revenue.id,    self.env['account.tax'],         100,               100          ],
            # taxes
            [self.account_revenue.id,    self.env['account.tax'],         30,                30           ],
            [self.account_revenue.id,    self.env['account.tax'],         15,                15           ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],         -down_pay_amt,     -down_pay_amt],
        ]
        self.assertRecordValues(invoice.line_ids, [dict(zip(expected[0], x)) for x in expected[1:]])

    def test_tax_brakedown_fixed_payment_method(self):
        self.sale_order.order_line[0].tax_id = self.tax_15 + self.tax_10
        self.sale_order.order_line[1].tax_id = self.tax_10
        self.sale_order.order_line[2].tax_id = self.tax_10
        self.make_downpayment(advance_payment_method='fixed', fixed_amount=222.5, amount=0)
        invoice = self.sale_order.invoice_ids
        down_pay_amt = 222.5
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                      'price_subtotal', 'price_total'  ],
            # base lines
            [self.account_revenue.id,    (self.tax_15 + self.tax_10).ids, 50,               62.5          ],
            [self.account_revenue.id,    self.tax_10.ids,                 100,              110           ],
            [self.account_revenue.id,    self.env['account.tax'],         50,               50            ],
            # taxes
            [self.account_revenue.id,    self.env['account.tax'],         15,               15            ],
            [self.account_revenue.id,    self.env['account.tax'],         7.5,              7.5           ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],         -down_pay_amt,     -down_pay_amt],
        ]
        self.assertRecordValues(invoice.line_ids, [dict(zip(expected[0], x)) for x in expected[1:]])

    def test_tax_brakedown_fixed_payment_method_with_taxes_on_all_lines(self):
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
            ['account_id',               'tax_ids',                      'price_subtotal', 'price_total'  ],
            # base lines
            [self.account_revenue.id,    self.tax_15.ids,                 50,               57.5          ],
            [self.account_revenue.id,    self.tax_10.ids,                 150,              165           ],
            # taxes
            [self.account_revenue.id,    self.env['account.tax'],         7.5,              7.5           ],
            [self.account_revenue.id,    self.env['account.tax'],         15,               15            ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],         -down_pay_amt,     -down_pay_amt],
        ]
        self.assertRecordValues(invoice.line_ids, [dict(zip(expected[0], x)) for x in expected[1:]])

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
            ['account_id',               'tax_ids',                       'price_subtotal', 'price_total' ],
            # base lines
            [self.account_revenue.id,    (tax_10_incl + self.tax_10).ids, 90.91,             109.09       ],
            [self.account_revenue.id,    self.tax_10.ids,                 200,               220          ],
            [self.account_revenue.id,    self.env['account.tax'],         100,               100          ],
            # taxes
            [self.account_revenue.id,    self.env['account.tax'],         29.09,             29.09        ],
            [self.account_revenue.id,    self.env['account.tax'],         9.09,              9.09         ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],         -down_pay_amt,     -down_pay_amt],
        ]
        self.assertRecordValues(invoice.line_ids, [dict(zip(expected[0], x)) for x in expected[1:]])

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
            ['account_id',               'tax_ids',                       'price_subtotal', 'price_total' ],
            # base lines
            [self.account_revenue.id,    (tax_10_pi_ba + self.tax_10).ids, 90.91,            110          ],
            [self.account_revenue.id,    self.tax_10.ids,                  200,              220          ],
            [self.account_revenue.id,    self.env['account.tax'],          100,              100          ],
            # taxes
            [self.account_revenue.id,    self.tax_10.ids,                  9.09,             10           ],
            [self.account_revenue.id,    self.env['account.tax'],          30,               30           ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],          -down_pay_amt,    -down_pay_amt],
        ]
        self.assertRecordValues(invoice.line_ids, [dict(zip(expected[0], x)) for x in expected[1:]])

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
            ['account_id',               'tax_ids',               'price_subtotal', 'price_total' ],
            # base lines
            [self.account_revenue.id,    self.tax_10.ids,         175,               192.5        ],
            [self.account_revenue.id,    self.tax_15.ids,         100,               115          ],
            [self.account_revenue.id,    self.env['account.tax'], 100,               100          ],
            # taxes
            [self.account_revenue.id,    self.env['account.tax'], 17.5,              17.5         ],
            [self.account_revenue.id,    self.env['account.tax'], 15,                15           ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'], -down_pay_amt,     -down_pay_amt],
        ]
        self.assertRecordValues(invoice.line_ids, [dict(zip(expected[0], x)) for x in expected[1:]])

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
            ['account_id',               'tax_ids',                       'price_subtotal', 'price_total' ],
            # base lines
            [self.account_revenue.id,    (tax_10_pi_ba + self.tax_10).ids, 68.18,            82.5         ],
            [self.account_revenue.id,    self.tax_10.ids,                  200,              220          ],
            [self.account_revenue.id,    self.env['account.tax'],          100,              100          ],
            # taxes
            [self.account_revenue.id,    self.tax_10.ids,                  6.82,             7.5          ],
            [self.account_revenue.id,    self.env['account.tax'],          27.5,             27.5         ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'],          -down_pay_amt,    -down_pay_amt],
        ]
        self.assertRecordValues(invoice.line_ids, [dict(zip(expected[0], x)) for x in expected[1:]])

    def test_tax_fixed_amount_brakedown(self):
        tax_10_fix = self.create_tax(10, {'amount_type': 'fixed'})
        self.sale_order.order_line[0].tax_id = tax_10_fix + self.tax_10
        self.sale_order.order_line[1].tax_id = self.tax_10
        self.sale_order.order_line[2].tax_id = self.tax_10
        self.make_downpayment()
        invoice = self.sale_order.invoice_ids
        down_pay_amt = self.sale_order.amount_total / 2
        # no tax breakdwon if fixed taxes
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',              'price_subtotal', 'price_total' ],
            # base lines
            [self.account_revenue.id,    self.env['account.tax'], down_pay_amt,     down_pay_amt ],
            # receivable
            [self.receivable_account.id, self.env['account.tax'], -down_pay_amt,    -down_pay_amt],
        ]
        self.assertRecordValues(invoice.line_ids, [dict(zip(expected[0], x)) for x in expected[1:]])
