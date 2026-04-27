from odoo import fields
from odoo.tests.common import tagged
from odoo.tools.misc import formatLang
from odoo.addons.account_avatax.tests.common import TestAccountAvataxCommon
from .mocked_so_response import generate_response


@tagged("-at_install", "post_install")
class TestSaleAvalara(TestAccountAvataxCommon):
    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()

        # This tax is deliberately wrong with an amount of 1. This is
        # used to make sure we use the tax values that Avatax returns
        # and not the tax values Odoo computes (these values would be
        # wrong if a user manually changes it or if they're partially
        # exempt).
        cls.tax_with_diff_amount = cls.env["account.tax"].create({
            'name': 'CA COUNTY TAX [075] (0.2500 %)',
            'company_id': cls.env.user.company_id.id,
            'amount': 1,
            'amount_type': 'percent',
        })

        cls.downpayment_account = cls.env['account.account'].sudo().create({
            'name': 'Customers - Payments on account received on orders',
            'account_type': 'liability_current',
            'code': '419100',
            'reconcile': True,
        })
        cls.env['ir.default'].set('product.category', 'property_account_downpayment_categ_id', cls.downpayment_account.id, company_id=cls.env.user.company_id.id)

        cls.sales_user = cls.env['res.users'].create({
            'name': 'Sales user',
            'login': 'sales',
            'email': 'sale_user@test.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id, cls.env.ref('sales_team.group_sale_salesman').id])],
        })
        cls.env = cls.env(user=cls.sales_user)
        cls.cr = cls.env.cr

        return res

    def assertOrder(self, order, mocked_response=None):
        if mocked_response:
            self.assertRecordValues(order, [{
                'amount_total': 97.68,
                'amount_untaxed': 90.0,
                'amount_tax': 7.68,
            }])
            totals = order.tax_totals
            subtotals = totals['subtotals']
            self.assertEqual(len(subtotals), 1)
            subtotal = subtotals[0]
            self.assertEqual(subtotal['base_amount_currency'], order.amount_untaxed)
            self.assertEqual(subtotal['tax_amount_currency'], order.amount_tax)
            self.assertEqual(totals['total_amount_currency'], order.amount_total)

            tax_groups = subtotal['tax_groups']
            self.assertEqual(len(tax_groups), 1, "There should be one tax group on the invoice containing all taxes.")
            self.assertEqual(tax_groups[0]['group_name'], 'Taxes')

            for avatax_line in mocked_response['lines']:
                so_line = order.order_line.filtered(lambda l: str(l.id) == avatax_line['lineNumber'].split(',')[1])
                self.assertRecordValues(so_line, [{
                    'price_subtotal': avatax_line['taxableAmount'],
                    'price_tax': avatax_line['tax'],
                    'price_total': avatax_line['taxableAmount'] + avatax_line['tax'],
                }])
        else:
            for line in order.order_line:
                product_name = line.product_id.display_name
                self.assertGreater(len(line.tax_id), 0, "Line with %s did not get any taxes set." % product_name)

            self.assertGreater(order.amount_tax, 0.0, "Invoice has a tax_amount of 0.0.")

    def _create_sale_order(self):
        return self.env['sale.order'].create({
            'user_id': self.sales_user.id,
            'partner_id': self.partner.id,
            'fiscal_position_id': self.fp_avatax.id,
            'date_order': '2021-01-01',
            'order_line': [
                (0, 0, {
                    'product_id': self.product_user.id,
                    'tax_id': None,
                    'price_unit': self.product_user.list_price,
                }),
                (0, 0, {
                    'product_id': self.product_user_discound.id,
                    'tax_id': None,
                    'price_unit': self.product_user_discound.list_price,
                }),
                (0, 0, {
                    'product_id': self.product_accounting.id,
                    'tax_id': None,
                    'price_unit': self.product_accounting.list_price,
                }),
                (0, 0, {
                    'product_id': self.product_expenses.id,
                    'tax_id': None,
                    'price_unit': self.product_expenses.list_price,
                }),
                (0, 0, {
                    'product_id': self.product_invoicing.id,
                    'tax_id': None,
                    'price_unit': self.product_invoicing.list_price,
                }),
            ]
        })

    def test_compute_on_send(self):
        order = self._create_sale_order()
        mocked_response = generate_response(order.order_line)
        with self._capture_request(return_value=mocked_response):
            order.action_quotation_send()
        self.assertOrder(order, mocked_response=mocked_response)

    def test_01_odoo_sale_order(self):
        order = self._create_sale_order()
        mocked_response = generate_response(order.order_line)
        with self._capture_request(return_value=mocked_response):
            order.button_external_tax_calculation()
        self.assertOrder(order, mocked_response=mocked_response)

    def test_integration_01_odoo_sale_order(self):
        with self._skip_no_credentials():
            order = self._create_sale_order()
            order.button_external_tax_calculation()
            self.assertOrder(order)

    def test_tax_round_globally(self):
        """The total amount of sale orders elligible for Avatax should never be computed with
        the 'round_globally' option but should instead use the 'round_per_line' mechanism"""
        self.env.company.sudo().tax_calculation_rounding_method = 'round_globally'
        order = self.env['sale.order'].create({
            'user_id': self.sales_user.id,
            'partner_id': self.partner.id,
            'fiscal_position_id': self.fp_avatax.id,
            'date_order': '2021-01-01',
            'order_line': [
                (0, 0, {
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'price_unit': 1.48,
                    'tax_id': self.tax_with_diff_amount.ids,
                }),
                (0, 0, {
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'price_unit': 1.48,
                    'tax_id': self.tax_with_diff_amount.ids,
                }),
            ],
        })
        self.assertEqual(order.amount_total, 2.98)

    def test_sale_order_downpayment(self):
        """ Test the expected down payment flow. Down payments are not sent to Avalara. We invoice everything on the final "regular"
        invoice, as if the down payments never happened.
        """
        order = self._create_sale_order()
        mocked_response = generate_response(order.order_line)
        with self._capture_request(return_value=mocked_response):
            order.action_confirm()

        downpayment_pct = 50
        payment_ctx = {
            "active_model": "sale.order",
            "active_ids": [order.id],
            "active_id": order.id,
        }
        wizard = (
            self.env["sale.advance.payment.inv"]
                .with_context(**payment_ctx)
                .create({
                    'advance_payment_method': 'percentage',
                    'amount': downpayment_pct,
                })
        )
        wizard.sudo().create_invoices()
        downpayment_invoice = order.invoice_ids

        with self._capture_request(return_value={'lines': [], 'summary': []}) as capture:
            downpayment_invoice.sudo().action_post()

        self.assertIsNone(capture.val, "Shouldn't call Avatax when posting a down payment invoice.")
        self.assertEqual(len(order.order_line.filtered(lambda line: not line.display_type)), 6, "Should have generated a new down payment line.")
        self.assertFalse(order.order_line.filtered('is_downpayment').tax_id, "Down payment lines on the quotation shouldn't have taxes.")
        self.assertAlmostEqual(downpayment_invoice.amount_total, order.amount_total * downpayment_pct / 100, msg="Down payment has the wrong amount.")
        self.assertEqual(downpayment_invoice.amount_tax, 0, "Down payment shouldn't have taxes.")
        self.assertEqual(downpayment_invoice.invoice_line_ids[0].account_id.id, self.downpayment_account.id, "Down payment has wrong account.")

        wizard = (
            self.env["sale.advance.payment.inv"]
                .with_context(**payment_ctx)
                .create({
                    'advance_payment_method': 'delivered',
                })
        )

        with self._capture_request(return_value={'lines': [], 'summary': []}) as capture:
            wizard.sudo().create_invoices()

        sent_lines = capture.val['json']['createTransactionModel']['lines']
        self.assertEqual(len(sent_lines), 5, "Should send only the regular lines.")


@tagged("-at_install", "post_install")
class TestAccountAvalaraSalesTaxItemsIntegration(TestAccountAvataxCommon):
    """https://developer.avalara.com/certification/avatax/sales-tax-badge/"""

    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()
        shipping_partner = cls.env["res.partner"].create({
            'name': "Shipping Partner",
            'street': "234 W 18th Ave",
            'city': "Columbus",
            'state_id': cls.env.ref("base.state_us_30").id, # Ohio
            'country_id': cls.env.ref("base.us").id,
            'zip': "43210",
        })

        with cls._capture_request(return_value={'lines': [], 'summary': []}) as capture:
            cls.sale_order = cls.env['sale.order'].create({
                'partner_id': cls.partner.id,
                'partner_shipping_id': shipping_partner.id,
                'fiscal_position_id': cls.fp_avatax.id,
                'date_order': '2021-01-01',
                'order_line': [
                    (0, 0, {
                        'product_id': cls.product.id,
                        'tax_id': None,
                        'price_unit': cls.product.list_price,
                    }),
                ]
            })
            cls.sale_order.button_external_tax_calculation()
        cls.captured_arguments = capture.val['json']['createTransactionModel']
        return res

    def test_item_code(self):
        """Identify customer code (number, ID) to pass to the AvaTax service."""
        line_model, line_id = self.captured_arguments['lines'][0]['number'].split(',')
        self.assertEqual(self.sale_order.order_line, self.env[line_model].browse(int(line_id)))

    def test_item_description(self):
        """Identify item/service/charge description to pass to the AvaTax service with a
        human-readable description or item name.
        """
        line_description = self.captured_arguments['lines'][0]['description']
        self.assertEqual(self.sale_order.order_line.name, line_description)

    def test_tax_code_mapping(self):
        """Association of an item or item group to an AvaTax Tax Code to describe the taxability
        (e.g. Clothing-Shirts – B-to-C).
        """
        tax_code = self.captured_arguments['lines'][0]['taxCode']
        self.assertEqual(self.product.avatax_category_id.code, tax_code)

    def test_doc_code(self):
        """Values that can come across to AvaTax as the DocCode."""
        code = self.captured_arguments['code']
        sent_so = self.env['sale.order'].search([('avatax_unique_code', '=', code)])
        self.assertEqual(self.sale_order, sent_so)

    def test_customer_code(self):
        """Values that can come across to AvaTax as the Customer Code."""
        customer_code = self.captured_arguments['customerCode']
        self.assertEqual(self.sale_order.partner_id.avalara_partner_code, customer_code)

    def test_doc_date(self):
        """Value that comes across to AvaTax as the DocDate."""
        doc_date = self.captured_arguments['date']  # didn't find anything with "DocDate"
        self.assertEqual(self.sale_order.date_order.date(), fields.Date.to_date(doc_date))

    def test_calculation_date(self):
        """Value that is used for Tax Calculation Date in AvaTax."""
        tax_date = self.captured_arguments['taxOverride']['taxDate']
        self.assertEqual(self.sale_order.date_order.date(), fields.Date.to_date(tax_date))

    def test_doc_type(self):
        """DocType used for varying stages of the transaction life cycle."""
        doc_type = self.captured_arguments['type']
        self.assertEqual('SalesOrder', doc_type)

    def test_header_level_destination_address(self):
        """Value that is sent to AvaTax for Destination Address at the header level."""
        destination_address = self.captured_arguments['addresses']['shipTo']
        self.assertEqual(destination_address, {
            'city': 'Columbus',
            'country': 'US',
            'line1': '234 W 18th Ave',
            'postalCode': '43210',
            'region': 'OH',
        })

    def test_header_level_origin_address(self):
        """Value that is sent to AvaTax for Origin Address at the header level."""
        origin_address = self.captured_arguments['addresses']['shipFrom']
        self.assertEqual(origin_address, {
            'city': 'San Francisco',
            'country': 'US',
            'line1': '250 Executive Park Blvd',
            'postalCode': '94134',
            'region': 'CA',
        })

    def test_quantity(self):
        """Value that is sent to AvaTax for the Quantity."""
        quantity = self.captured_arguments['lines'][0]['quantity']
        self.assertEqual(self.sale_order.order_line.product_uom_qty, quantity)

    def test_amount(self):
        """Value that is sent to AvaTax for the Amount."""
        amount = self.captured_arguments['lines'][0]['amount']
        self.assertEqual(self.sale_order.order_line.price_subtotal, amount)

    def test_tax_code(self):
        """Value that is sent to AvaTax for the Tax Code."""
        tax_code = self.captured_arguments['lines'][0]['taxCode']
        self.assertEqual(self.sale_order.order_line.product_id.avatax_category_id.code, tax_code)

    def test_sales_order(self):
        """Ensure that invoices are processed through a logical document lifecycle."""
        self.assertEqual(self.captured_arguments['type'], 'SalesOrder')
        with self._capture_request({'lines': [], 'summary': []}) as capture:
            self.sale_order.action_quotation_send()
            self.sale_order.action_confirm()
            invoice = self.sale_order._create_invoices()
            invoice.button_external_tax_calculation()
        self.assertEqual(capture.val['json']['createTransactionModel']['type'], 'SalesInvoice')

        with self._capture_request({'lines': [], 'summary': []}) as capture:
            invoice.action_post()
        self.assertTrue(capture.val['json']['createTransactionModel']['commit'])

    def test_commit_tax(self):
        """Ensure that invoices are committed/posted for reporting appropriately."""
        with self._capture_request({'lines': [], 'summary': []}) as capture:
            self.sale_order.action_quotation_send()
            self.sale_order.action_confirm()
            invoice = self.sale_order._create_invoices()
            invoice.action_post()
        self.assertTrue(capture.val['json']['createTransactionModel']['commit'])

    def test_merge_sale_orders(self):
        """Ensure sale orders with different shipping partner are not merged
           in the same invoice
        """
        shipping_partner_b = self.env["res.partner"].create({
            'name': "Shipping Partner B",
            'street': "4557 De Silva St",
            'city': "Freemont",
            'state_id': self.env.ref("base.state_us_13").id,
            'country_id': self.env.ref("base.us").id,
            'zip': "94538",
        })

        with self._capture_request(return_value={'lines': [], 'summary': []}):
            sale_order_b = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'partner_shipping_id': shipping_partner_b.id,
                'fiscal_position_id': self.fp_avatax.id,
                'date_order': '2021-01-01',
                'order_line': [
                    (0, 0, {
                        'product_id': self.product.id,
                        'tax_id': None,
                        'price_unit': self.product.list_price,
                    }),
                ]
            })
            orders = self.sale_order | sale_order_b
            orders.action_confirm()
            orders._create_invoices()
        self.assertEqual(len(orders.invoice_ids), 2, "Different invoices should be created")

    def test_empty_sale_order(self):
        self.sale_order.order_line = False
        with self._capture_request({'lines': [], 'summary': []}) as capture:
            self.sale_order.button_external_tax_calculation()
            self.assertIsNone(capture.val, 'Should not call Avatax without lines')
