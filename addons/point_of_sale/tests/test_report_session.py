# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo

from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestReportSession(TestPointOfSaleDataHttpCommon):
    def test_report_session(self):
        self.pos_config.open_ui()
        self.product_awesome_item.write({
            'categ_id': self.product_category.id,
            'list_price': 110,
            'taxes_id': [(6, 0, self.tax_10_include.ids)],
        })
        self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method_split, 'amount': 60},
            {'payment_method_id': self.bank_payment_method, 'amount': 50},
        ], False, False, self.partner_one)

        session = self.pos_config.current_session_id
        session.action_pos_session_closing_control(
            bank_payment_method_diffs={self.bank_payment_method_split.id: 50, self.bank_payment_method.id: 40})

        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details(session_ids=[session.id])
        split_payment_bank = [p for p in report['payments'] if p.get('id', 0) == self.bank_payment_method_split.id]
        # self.assertEqual(split_payment_bank[0]['cash_moves'][0]['amount'], 50)  TODO MODA
        bank_payment = [p for p in report['payments'] if p.get('id', 0) == self.bank_payment_method.id]
        # self.assertEqual(bank_payment[0]['cash_moves'][0]['amount'], 40)  TODO WAN
        self.assertEqual(report['products_info']['total'], 100, "Total amount of products should be 100, as we want total without tax")
        self.assertEqual(report['products'][0]['products'][0]['base_amount'], 100, "Base amount of product should be 100, as we want price without tax")

    def test_report_session_2(self):
        self.product_awesome_item.write({
            'categ_id': self.product_category.id,
            'list_price': 100,
        })
        self.pos_config.open_ui()
        lines = [{'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0}]
        self.create_order(lines, [
            {'payment_method_id': self.bank_payment_method, 'amount': 100},
        ], False, False, self.partner_one)
        self.create_order(lines, [
            {'payment_method_id': self.cash_payment_method, 'amount': 100},
        ], False, False, self.partner_one)
        self.pos_config.current_session_id.action_pos_session_closing_control()

        self.pos_config.open_ui()
        session_id_2 = self.pos_config.current_session_id.id
        self.create_order(lines, [
            {'payment_method_id': self.bank_payment_method, 'amount': 100},
        ], False, False, self.partner_one)
        self.create_order(lines, [
            {'payment_method_id': self.cash_payment_method, 'amount': 100},
        ], False, False, self.partner_one)
        self.pos_config.current_session_id.action_pos_session_closing_control()

        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details()
        for payment in report['payments']:
            session_name = self.env['pos.session'].browse(payment['session']).name
            payment_method_name = self.env['pos.payment.method'].browse(payment['id']).name
            self.assertEqual(payment['name'], payment_method_name + " " + session_name)

        pdf = self.env['ir.actions.report']._render_qweb_pdf('point_of_sale.sale_details_report', res_ids=session_id_2)
        self.assertTrue(pdf)

    def test_report_listing(self):
        self.pos_config.open_ui()
        (self.product_awesome_item + self.product_awesome_article).write({
            'categ_id': self.product_category.id,
            'list_price': 150,
            'taxes_id': [(6, 0, self.tax_10_include.ids)],
        })
        order = self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0},
            {'product_id': self.product_awesome_article.product_variant_id, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.cash_payment_method, 'amount': 100},
            {'payment_method_id': self.bank_payment_method, 'amount': 200},
        ], False, False, self.partner_one)

        order_report_lines = self.env['report.pos.order'].sudo().search([('order_id', '=', order.id)])
        self.assertEqual(len(order_report_lines), 2)
        self.assertEqual(order_report_lines[0].payment_method_id.id, order_report_lines[1].payment_method_id.id)

        for order in order_report_lines:
            self.assertEqual(order.price_total, 150.0)
            self.assertEqual(order.nbr_lines, 1)
            self.assertEqual(order.product_qty, 1)

        order_report_lines_count_product1 =self.env['report.pos.order'].sudo().search_count([
            ('product_id', '=', self.product_awesome_item.product_variant_id.id)])
        order_report_lines_count_product2 = self.env['report.pos.order'].sudo().search_count([
            ('product_id', '=', self.product_awesome_article.product_variant_id.id)])

        self.assertEqual(order_report_lines_count_product1, 1)
        self.assertEqual(order_report_lines_count_product2, 1)

    def test_report_session_3(self):
        self.pos_config.open_ui()
        self.product_awesome_item.write({
            'categ_id': self.product_category.id,
            'list_price': 0,
        })
        lines = [{
            'name': "OL/0001",
            'product_id': self.product_awesome_item.product_variant_id,
            'discount': 0,
            'qty': 14.9,
        }]
        self.create_order(lines, [
            {'payment_method_id': self.bank_payment_method, 'amount': 0},
        ], False, False, self.partner_one)
        lines[0]['qty'] = 59.7
        self.create_order(lines, [
            {'payment_method_id': self.bank_payment_method, 'amount': 0},
        ], False, False, self.partner_one)
        self.pos_config.current_session_id.action_pos_session_closing_control()
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details()
        self.assertEqual(report['products'][0]['products'][0]['quantity'], 74.6, "Quantity of product should be 74.6, as we want the sum of the quantity of the two orders")
