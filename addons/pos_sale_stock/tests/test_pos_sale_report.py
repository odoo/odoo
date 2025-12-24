from odoo import fields
from odoo.addons.pos_stock.tests.common import TestPosStockCommon
from odoo.addons.pos_stock.tests.test_frontend import TestPosStockHttpCommon
from odoo.addons.pos_sale.tests.test_pos_sale_report import TestPoSSaleReport


class TestPoSSaleStockReport(TestPoSSaleReport, TestPosStockCommon, TestPosStockHttpCommon):

    def test_different_shipping_address(self):
        product_0 = self.create_product('Product 0', self.categ_basic, 0.0, 0.0)
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.customer.id,
            'partner_shipping_id': self.other_customer.id,
            'order_line': [(0, 0, {
                'product_id': product_0.id,
            })],
        })
        self.open_new_session()

        data = self.create_ui_order_data([(product_0, 1)], {}, self.customer, True)
        data['lines'][0][2]['sale_order_origin_id'] = sale_order.id
        data['lines'][0][2]['sale_order_line_id'] = sale_order.order_line[0].id
        order_ids = self.env['pos.order'].sync_from_ui([data])

        move_id = self.env['account.move'].browse(order_ids['pos.order'][0]['account_move'])
        self.assertEqual(move_id.partner_id.id, self.customer.id)
        self.assertEqual(move_id.partner_shipping_id.id, self.other_customer.id)

    def test_warehouse(self):

        self.open_new_session()
        session = self.pos_session
        orders = []

        # Process two orders
        orders.append(self.create_ui_order_data([(self.product0, 3)]))
        self.env['pos.order'].sync_from_ui(orders)

        session.action_pos_session_closing_control()

        reports = self.env['sale.report'].sudo().search([('product_id', '=', self.product0.id)], order='id', limit=2)
        self.assertEqual(reports[0].warehouse_id.id, self.config.picking_type_id.warehouse_id.id)

    def test_qty_deliverd_qty_to_deliver_in_sales_report(self):
        """
            Track the quantity of products ordered based on their picking state. for example : If an order is created for 3 products
            with the option to ship later, the products will be listed under qty_to_deliver in the sales report until the picking state
            is validated. Once validated and marked as done, the quantity will shift to qty_delivered.
        """
        self.config.ship_later = True
        self.open_new_session()
        session = self.pos_session

        orders = []

        orders.append(self.create_ui_order_data([(self.product0, 5, 100), (self.product0, 3)], {}, self.partner_1))
        orders[0]['shipping_date'] = fields.Date.to_string(fields.Date.today())

        order = self.env['pos.order'].sync_from_ui(orders)
        order = self.env['pos.order'].browse(order['pos.order'][0]['id'])

        session.action_pos_session_closing_control()

        report = self.env['sale.report'].sudo().search([('product_id', '=', self.product0.id)], order='id')

        self.assertEqual(sum(report.mapped('qty_to_deliver')), 8)
        self.assertEqual(sum(report.mapped('qty_delivered')), 0)

        order.picking_ids.move_ids.quantity = 8.0
        order.picking_ids.button_validate()
        # flush computations and clear the cache before checking again the report
        self.env.flush_all()
        self.env.transaction.clear()

        report = self.env['sale.report'].sudo().search([('product_id', '=', self.product0.id)], order='id')

        self.assertEqual(sum(report.mapped('qty_to_deliver')), 0)
        self.assertEqual(sum(report.mapped('qty_delivered')), 8)

    def test_sale_stock_report_select(self):
        select_statement = self.env['sale.report']._select_pos()
        pos_currency_rate = self.env['sale.report']._case_value_or_one('pos.currency_rate')
        account_currency_table = self.env['sale.report']._case_value_or_one('account_currency_table.rate')
        untaxed_delivered_amount = f"(CASE WHEN pos.account_move IS NOT NULL THEN SUM(l.price_unit * l.qty_delivered) ELSE 0 END) / MIN({pos_currency_rate}) * {account_currency_table}"
        self.assertTrue(untaxed_delivered_amount in select_statement)
