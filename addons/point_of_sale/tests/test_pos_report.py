# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

import odoo

from odoo import Command
from odoo.addons.point_of_sale.tests.common import CommonPosTest


@odoo.tests.tagged('post_install', '-at_install')
class TestPosSession(CommonPosTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.pos_config_usd

    def test_report_session(self):

        self.tax1 = self.env['account.tax'].create({
            'name': 'Tax 1',
            'amount': 10,
            'price_include_override': 'tax_included',
        })
        self.product1 = self.create_product('Product A', 110, tax_ids=self.tax1.ids)

        second_bank_pm = self.bank_pm.copy({'name': 'Second Bank'})
        self.config.payment_method_ids |= second_bank_pm
        session = self.open_new_session()
        session_id = session.id
        self.create_pos_order(
            [[self.product1]],
            payments=[[second_bank_pm, 60], [self.bank_pm, 50]],
            customer=self.partner_a,
        )
        self.close_pos_session()

        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details(session_ids=[session_id])
        # self.assertEqual(bank_payment[0]['cash_moves'][0]['amount'], 40)  TODO WAN
        self.assertEqual(report['products_info']['total'], 100, "Total amount of products should be 100, as we want total without tax")
        self.assertEqual(report['products'][0]['products'][0]['base_amount'], 100, "Base amount of product should be 100, as we want price without tax")
        self.assertEqual(report['products'][0]['total'], 100, "Category total should be 100, as it is tax excluded")
        self.assertEqual(report['products'][0]['total_paid'], 110, "Category total paid should be 110, as it matches the price paid for its products")

    def test_report_session_2(self):
        self.product1 = self.create_product('Product A', 100)

        for _ in range(2):
            session = self.open_new_session()
            self.create_orders([
                {'lines': [[self.product1]], 'payments': [[payment_method, 100]], 'customer': self.partner_a}
                for payment_method in (self.bank_pm, self.cash_pm)
            ])
            self.close_pos_session()
        session_id_2 = session.id

        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details()
        for payment in report['payments']:
            session_name = self.env['pos.session'].browse(payment['session']).name
            payment_method_name = self.env['pos.payment.method'].browse(payment['id']).name
            self.assertEqual(payment['name'], payment_method_name + " " + session_name)

        pdf = self.env['ir.actions.report']._render_qweb_pdf('point_of_sale.sale_details_report', res_ids=session_id_2)
        self.assertTrue(pdf)

    def test_report_listing(self):
        product1 = self.create_product('Product 1', 150)
        product2 = self.create_product('Product 2', 150)

        (product1 | product2).taxes_id = self.taxes['tax10']
        self.open_new_session()
        order = self.create_pos_order(
            [[product1], [product2]],
            payments=[[payment_method, amount] for amount in (65, 100) for payment_method in (self.cash_pm, self.bank_pm)],
        )

        order_report_lines = self.env['report.pos.order'].sudo().search([('order_id', '=', order.id)])

        self.assertEqual(len(order_report_lines), 2)
        self.assertEqual(order_report_lines[0].payment_method_id.id, order_report_lines[1].payment_method_id.id)

        for order in order_report_lines:
            self.assertEqual(order.price_total, 165.0)
            self.assertEqual(order.nbr_lines, 1)
            self.assertEqual(order.product_qty, 1)

        order_report_lines_count_product1 = self.env['report.pos.order'].sudo().search_count([('product_id', '=', product1.id)])
        order_report_lines_count_product2 = self.env['report.pos.order'].sudo().search_count([('product_id', '=', product2.id)])

        self.assertEqual(order_report_lines_count_product1, 1)
        self.assertEqual(order_report_lines_count_product2, 1)

    def test_report_session_3(self):
        self.product1 = self.create_product('Product A', 100)
        self.open_new_session()
        self.create_orders([
            {
                'lines': [[self.product1, quantity, 0, {'price_unit': 0}]],
                'payments': [[self.bank_pm, 0]],
                'customer': self.partner_a,
            }
            for quantity in (14.9, 59.7)
        ])
        self.close_pos_session()
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details()
        self.assertEqual(report['products'][0]['products'][0]['quantity'], 74.6, "Quantity of product should be 74.6, as we want the sum of the quantity of the two orders")

    def test_report_bank_expected_different_than_counted(self):
        """
        Test that in the pos session report, the difference between the expected and counted bank payment is correct.
        Test both with a default outstanding account on the payment and without.
        """
        self.tax1 = self.env['account.tax'].create({
            'name': 'Tax 1',
            'amount': 10,
            'price_include_override': 'tax_included',
        })
        self.product1 = self.create_product('Product A', 100, tax_ids=self.tax1.ids)

        self.bank_pm.outstanding_account_id = self.outstanding_bank.id
        self.config.open_ui()

        session1_id = self.config.current_session_id.id
        self.create_pos_order(
            [[self.product1]],
            payments=[[self.bank_pm, 100]],
            customer=self.partner_a,
        )

        self.config.current_session_id.close_session_from_ui(
            payment_method_closing={self.bank_pm.id: 80})
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details(session_ids=[session1_id])
        self.assertEqual(next(payment for payment in report['payments'] if payment.get('id') == self.bank_pm.id)['money_difference'], -20)

        self.bank_pm.outstanding_account_id = False
        self.config.open_ui()

        session2_id = self.config.current_session_id.id
        self.create_pos_order(
            [[self.product1]],
            payments=[[self.bank_pm, 100]],
            customer=self.partner_a,
        )

        self.config.current_session_id.close_session_from_ui(
            payment_method_closing={self.bank_pm.id: 80})
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details(session_ids=[session2_id])
        self.assertEqual(next(payment for payment in report['payments'] if payment.get('id') == self.bank_pm.id)['money_difference'], -20)

    def test_report_session_4(self):
        self.tax1 = self.env['account.tax'].create({
            'name': 'Tax 1',
            'amount': 10,
            'price_include_override': 'tax_included',
        })

        self.tax2 = self.env['account.tax'].create({
            'name': 'Tax 2',
            'amount': 15,
            'price_include_override': 'tax_included',
        })
        self.product1 = self.create_product('Product A', 125, tax_ids=(self.tax1 | self.tax2).ids)

        self.open_new_session()
        self.create_pos_order(
            [[self.product1]],
            payments=[[self.bank_pm, 125]],
            customer=self.partner_a,
        )
        self.close_pos_session()
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details()
        self.assertEqual(report["taxes_info"]["base_amount"], 100, "Base amount should be equal to 100")

    def test_report_session_category_qty_round(self):
        self.config.open_ui()
        quantities = [12.45, 88.21, 45.09, 7.33, 56.12, 92.84, 31.56, 19.47, 64.91, 5.02, 77.38, 41.65, 23.19, 99.72, 10.88]
        products = [self.create_product(f'Product {i}', 100) for i in range(len(quantities))]
        total = sum(quantities)
        self.create_orders([
            {
                'lines': [[product, quantity, 0, {'price_unit': 1}] for product, quantity in zip(products, quantities)],
                'payments': [[self.bank_pm, total]],
                'customer': self.partner_a,
            }
            for _ in range(5)
        ])
        self.close_pos_session()
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details()
        self.assertAlmostEqual(report['products'][0]['qty'], 675.82 * 5)  # The test create 5 orders
        self.assertAlmostEqual(report['products'][0]['total'], 675.82 * 5)  # The test create 5 orders

    def test_session_report_with_fp_and_discount(self):
        fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'Fiscal Position 10% to 20%',
        })
        self.tax1 = self.env['account.tax'].create({
            'name': 'Tax 1 - 10%',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 10,
        })
        self.tax2 = self.env['account.tax'].create({
            'name': 'Tax 2 - 20%',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 20,
            'fiscal_position_ids': [Command.link(fiscal_position.id)],
            'original_tax_ids': [Command.link(self.tax1.id)],
        })
        self.product1 = self.create_product('Vanela Gathiya', 100, tax_ids=self.tax1.ids)
        self.config.open_ui()
        order = self.create_pos_order(
            [[self.product1, 1, 10]],
            payments=[[self.bank_pm, 108]],
            customer=self.partner_a,
            fiscal_position_id=fiscal_position.id,
        )
        self.assertEqual(order.lines.tax_ids_after_fiscal_position, self.tax2)
        self.close_pos_session()
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details()
        self.assertEqual(report["discount_amount"], 12.0, "Discount amount should be equal to 12.0")
        self.assertEqual(report["taxes_info"]["base_amount"], 90.0, "Base amount should be equal to 90.0")

    def test_session_report_discount_with_refund(self):
        """A refunded discount must be subtracted, not added, in the report."""
        product = self.create_product('Discounted Book', 100)
        self.config.open_ui()

        # Sell 2 units at 10% discount: subtotal 200 -> 180, discount 20.
        order = self.create_pos_order(
            [[product, 2, 10]],
            payments=[[self.bank_pm, 180]],
            customer=self.partner_a,
        )
        refund = self.refund_pos_order(order, self.bank_pm, -180)
        self.assertEqual(refund.lines[0].discount, 10)
        self.assertEqual(refund.lines[0].qty, -2)
        self.assertEqual(refund.lines[0].price_subtotal_incl, 180)

        self.close_pos_session()
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details()

        # Sale discount is 200 - 180 = 20; the refund must cancel it out.
        self.assertEqual(
            report["discount_amount"], 0.0,
            "A fully refunded discounted line must net its discount to zero",
        )

    def test_report_header_reflects_actual_order_sessions(self):
        """A date-range report whose orders span multiple sessions (e.g. one
        closed and one still open) must show state='multiple' rather than
        displaying the closed session's name as if it were a single-session Z
        report.
        """
        product = self.create_product('Test Product', 100)
        # Session 1: open, create an order, close.
        self.open_new_session()
        self.create_pos_order([[product]], payments=[[self.bank_pm, 100]], customer=self.partner_a)
        self.close_pos_session()

        # Session 2: open, create an order, intentionally leave open.
        session2 = self.open_new_session()
        order2 = self.create_pos_order([[product]], payments=[[self.bank_pm, 100]], customer=self.partner_a)

        # Run the report via date range (config_ids only, no session_ids).
        # Both sessions' orders fall in the default date range (today).
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details(
            config_ids=self.config.ids,
        )

        self.assertEqual(report['state'], 'multiple',
            "Header state must be 'multiple' when orders span more than one session")
        self.assertFalse(report['session_name'],
            "session_name must be False when orders come from multiple sessions")
        self.assertEqual(report['nbr_orders'], 2,
            "Both sessions' orders should be included in the report body")

        self.close_pos_session()
        report2 = self.env['report.point_of_sale.report_saledetails'].get_sale_details(
            config_ids=self.config.ids,
        )
        self.assertEqual(report2['state'], 'multiple',
            "Two closed sessions in range must still produce state='multiple'")
        self.assertEqual(report2['nbr_orders'], 2)

        # Query a window strictly inside session2 (date range, no session_ids)
        # that contains one of session2's orders. The header must show that
        # window, not session2's start_at/stop_at.
        date_start = session2.start_at + timedelta(minutes=1)
        date_stop = date_start + timedelta(hours=1)
        order2.date_order = date_start + timedelta(minutes=10)
        report3 = self.env['report.point_of_sale.report_saledetails'].get_sale_details(
            date_start=date_start, date_stop=date_stop, config_ids=self.config.ids,
        )
        self.assertEqual(report3['nbr_orders'], 1)
        self.assertEqual(report3['state'], 'multiple')
        self.assertEqual(report3['date_start'], date_start)
        self.assertEqual(report3['date_stop'], date_stop)

    def test_report_sale_details_total_with_cash_rounding(self):
        """Test that the sale details report shows the cash rounding amount."""
        rounding_method = self.env['account.cash.rounding'].create({
            'name': 'Rounding 0.05',
            'rounding': 0.05,
            'profit_account_id': self.company_data['default_account_revenue'].id,
            'loss_account_id': self.company_data['default_account_expense'].id,
        })
        self.config.write({
            'cash_rounding': True,
            'rounding_method': rounding_method.id,
        })
        product = self.create_product('Product Rounding', 10.42)

        self.config.open_ui()

        self.create_pos_order([[product]], payments=[[self.cash_pm, 10.40]])
        session = self.close_pos_session()

        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details(session_ids=[session.id])
        self.assertAlmostEqual(
            report['cash_rounding_total'], 10.40 - 10.42, places=2,
            msg="Cash rounding total should equal sum of (amount_paid - amount_total) across orders"
        )

    def test_report_pos_order_0(self):
        """Test the margin and price_total of a PoS Order with no taxes."""
        product1 = self.create_product('Product 1', 150)
        self.categ_all = self.env['pos.category'].search([])
        product1.write({'pos_categ_ids': [odoo.Command.set(self.categ_all.ids)]})

        self.open_new_session()
        self.create_pos_order([[product1]], payments=[], state='draft')

        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        reports = self.env['report.pos.order'].sudo().search([('product_id', '=', product1.id)], order='id')

        self.assertEqual(len(reports.ids), 1)
        self.assertEqual(reports[0].margin, 150)
        self.assertEqual(reports[0].price_total, 150)

    def test_report_pos_order_1(self):
        """Test the margin and price_total of a PoS Order with taxes."""

        product1 = self.create_product('Product 1', 150, tax_ids=self.taxes['tax10'].ids)

        self.open_new_session()

        self.create_pos_order([[product1]], payments=[], state='draft')

        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        reports = self.env['report.pos.order'].sudo().search([('product_id', '=', product1.id)], order='id')

        self.assertEqual(reports[0].margin, 150)
        self.assertEqual(reports[0].price_total, 165)

    def test_report_pos_order_2(self):
        """Test the margin and price_total of a PoS Order with discount and no taxes"""

        product1 = self.create_product('Product 1', 150)

        self.open_new_session()

        self.create_pos_order([[product1, 1, 10]], payments=[], state='draft')

        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        reports = self.env['report.pos.order'].sudo().search([('product_id', '=', product1.id)], order='id')

        self.assertEqual(reports[0].margin, 135)
        self.assertEqual(reports[0].price_total, 135)

    def test_report_pos_order_margin_other_currency(self):
        """Test that the currency_rate set on the order is correctly taken into account when generating the report"""

        product1 = self.create_product('Product 1', 150)
        self.open_new_session()

        self.create_pos_order([[product1, 1, 0, {'price_unit': 300}]], payments=[], state='draft', currency_rate=2)

        reports = self.env['report.pos.order'].sudo().search([('product_id', '=', product1.id)], order='id')

        self.assertEqual(reports[0].margin, 150)
        self.assertEqual(reports[0].price_subtotal_excl, 150)
        self.assertEqual(reports[0].price_total, 150)
