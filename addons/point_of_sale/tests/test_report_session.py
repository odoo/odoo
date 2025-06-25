# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo

from odoo.addons.point_of_sale.tests.common import TestPoSCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestReportSession(TestPoSCommon):

    def setUp(self):
        super(TestReportSession, self).setUp()
        self.config = self.basic_config

    def test_report_session(self):

        self.tax1 = self.env['account.tax'].create({
            'name': 'Tax 1',
            'amount': 10,
            'price_include_override': 'tax_included',
        })
        self.product1 = self.create_product('Product A', self.categ_basic, 110, self.tax1.id)

        self.config.open_ui()
        session_id = self.config.current_session_id.id
        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': session_id,
            'partner_id': self.partner_a.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product1.id,
                'price_unit': 110,
                'discount': 0,
                'qty': 1,
                'tax_ids': [[6, False, [self.tax1.id]]],
                'price_subtotal': 100,
                'price_subtotal_incl': 110,
            })],
            'pricelist_id': self.config.pricelist_id.id,
            'amount_paid': 110.0,
            'amount_total': 110.0,
            'amount_tax': 10.0,
            'amount_return': 0.0,
            'last_order_preparation_change': '{}',
            'to_invoice': False,
        })

        self.make_payment(order, self.bank_split_pm1, 60)
        self.make_payment(order, self.bank_pm1, 50)

        self.config.current_session_id.action_pos_session_closing_control(bank_payment_method_diffs={self.bank_split_pm1.id: 50, self.bank_pm1.id: 40})

        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details(session_ids=[session_id])
        split_payment_bank = [p for p in report['payments'] if p.get('id', 0) == self.bank_split_pm1.id]
        self.assertEqual(split_payment_bank[0]['cash_moves'][0]['amount'], 50)
        bank_payment = [p for p in report['payments'] if p.get('id', 0) == self.bank_pm1.id]
        # self.assertEqual(bank_payment[0]['cash_moves'][0]['amount'], 40)  TODO WAN
        self.assertEqual(report['products_info']['total'], 100, "Total amount of products should be 100, as we want total without tax")
        self.assertEqual(report['products'][0]['products'][0]['base_amount'], 100, "Base amount of product should be 100, as we want price without tax")

    def test_report_session_2(self):

        self.product1 = self.create_product('Product A', self.categ_basic, 100)

        self.config.open_ui()
        session_id_1 = self.config.current_session_id.id
        order_info = {'company_id': self.env.company.id,
                      'session_id': session_id_1,
                      'partner_id': self.partner_a.id,
                      'lines': [(0, 0, {
                          'name': "OL/0001",
                          'product_id': self.product1.id,
                          'price_unit': 100,
                          'discount': 0,
                          'qty': 1,
                          'tax_ids': [],
                          'price_subtotal': 100,
                          'price_subtotal_incl': 100,
                      })],
                      'pricelist_id': self.config.pricelist_id.id,
                      'amount_paid': 100.0,
                      'amount_total': 100.0,
                      'amount_tax': 0.0,
                      'amount_return': 0.0,
                      'to_invoice': False,
                      }

        order = self.env['pos.order'].create(order_info)
        self.make_payment(order, self.bank_pm1, 100)

        order = self.env['pos.order'].create(order_info)
        self.make_payment(order, self.cash_pm1, 100)

        self.config.current_session_id.action_pos_session_closing_control()

        self.config.open_ui()
        session_id_2 = self.config.current_session_id.id
        order_info['session_id'] = session_id_2
        order = self.env['pos.order'].create(order_info)
        self.make_payment(order, self.bank_pm1, 100)

        order = self.env['pos.order'].create(order_info)
        self.make_payment(order, self.cash_pm1, 100)

        self.config.current_session_id.action_pos_session_closing_control()

        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details()
        for payment in report['payments']:
            session_name = self.env['pos.session'].browse(payment['session']).name
            payment_method_name = self.env['pos.payment.method'].browse(payment['id']).name
            self.assertEqual(payment['name'], payment_method_name + " " + session_name)

        pdf = self.env['ir.actions.report']._render_qweb_pdf('point_of_sale.sale_details_report', res_ids=session_id_2)
        self.assertTrue(pdf)

    def test_report_listing(self):
        product1 = self.create_product('Product 1', self.categ_basic, 150)
        product2 = self.create_product('Product 2', self.categ_basic, 150)

        cash_payment_method = self.env['pos.payment.method'].create({
            'name': 'Cash',
            'receivable_account_id': self.company_data['default_account_receivable'].id,
            'journal_id': self.company_data['default_journal_cash'].id,
            'company_id': self.env.company.id,
        })
        bank_payment_method = self.env['pos.payment.method'].create({
            'name': 'Bank',
            'journal_id': self.company_data['default_journal_bank'].id,
            'receivable_account_id': self.company_data['default_account_receivable'].id,
            'company_id': self.env.company.id,
        })
        self.config.write({'payment_method_ids': [(4, bank_payment_method.id), (4, cash_payment_method.id)]})

        self.open_new_session()
        session = self.pos_session

        self.tax_sale_a['amount'] = 10
        order = self.env['pos.order'].create({
            'session_id': session.id,
            'lines': [(0, 0, {
                'name': "TR/0001",
                'product_id': product1.id,
                'price_unit': 150,
                'discount': 0,
                'qty': 1.0,
                'price_subtotal': 150,
                'tax_ids': [(6, 0, self.tax_sale_a.ids)],
                'price_subtotal_incl': 165,
            }), (0, 0, {
                'name': "TR/0001",
                'product_id': product2.id,
                'price_unit': 150,
                'discount': 0,
                'qty': 1.0,
                'price_subtotal': 150,
                'tax_ids': [(6, 0, self.tax_sale_a.ids)],
                'price_subtotal_incl': 165,
            })],
            'amount_total': 330.0,
            'amount_tax': 30.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })
        payment_context = {"active_ids": order.ids, "active_id": order.id}

        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create([{
            'amount': am,
            'payment_method_id': pm
        } for am in [65, 100] for pm in [cash_payment_method.id, bank_payment_method.id]])
        for payment in order_payment:
            payment.with_context(**payment_context).check()

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
        self.product1 = self.create_product('Product A', self.categ_basic, 100)
        self.config.open_ui()
        session_id = self.config.current_session_id.id
        order_info = {'company_id': self.env.company.id,
                'session_id': session_id,
                'partner_id': self.partner_a.id,
                'lines': [(0, 0, {
                    'name': "OL/0001",
                    'product_id': self.product1.id,
                    'price_unit': 0,
                    'discount': 0,
                    'qty': 14.9,
                    'tax_ids': [],
                    'price_subtotal': 0,
                    'price_subtotal_incl': 0,
                })],
                'pricelist_id': self.config.pricelist_id.id,
                'amount_paid': 0.0,
                'amount_total': 0.0,
                'amount_tax': 0.0,
                'amount_return': 0.0,
                'to_invoice': False,
                }
        order = self.env['pos.order'].create(order_info)
        self.make_payment(order, self.bank_pm1, 0)
        order_info['lines'][0][2]['qty'] =  59.7
        order = self.env['pos.order'].create(order_info)
        self.make_payment(order, self.bank_pm1, 0)
        self.config.current_session_id.action_pos_session_closing_control()
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
        self.product1 = self.create_product('Product A', self.categ_basic, 100, self.tax1.id)

        self.bank_pm1.outstanding_account_id = self.outstanding_bank.id
        self.config.open_ui()

        session1_id = self.config.current_session_id.id
        order1 = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': session1_id,
            'partner_id': self.partner_a.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product1.id,
                'price_unit': 100,
                'discount': 0,
                'qty': 1,
                'tax_ids': [[6, False, [self.tax1.id]]],
                'price_subtotal': 100,
                'price_subtotal_incl': 100,
            })],
            'pricelist_id': self.config.pricelist_id.id,
            'amount_paid': 100.0,
            'amount_total': 100.0,
            'amount_tax': 10.0,
            'amount_return': 0.0,
            'last_order_preparation_change': '{}',
            'to_invoice': False,
        })

        self.make_payment(order1, self.bank_pm1, 100)

        self.config.current_session_id.action_pos_session_closing_control(
            bank_payment_method_diffs={self.bank_pm1.id: -20})
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details(session_ids=[session1_id])
        self.assertEqual(report['payments'][1]['money_difference'], -20)

        self.bank_pm1.outstanding_account_id = False
        self.config.open_ui()

        session2_id = self.config.current_session_id.id
        order2 = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': session2_id,
            'partner_id': self.partner_a.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product1.id,
                'price_unit': 100,
                'discount': 0,
                'qty': 1,
                'tax_ids': [[6, False, [self.tax1.id]]],
                'price_subtotal': 100,
                'price_subtotal_incl': 100,
            })],
            'pricelist_id': self.config.pricelist_id.id,
            'amount_paid': 100.0,
            'amount_total': 100.0,
            'amount_tax': 10.0,
            'amount_return': 0.0,
            'last_order_preparation_change': '{}',
            'to_invoice': False,
        })

        self.make_payment(order2, self.bank_pm1, 100)

        self.config.current_session_id.action_pos_session_closing_control(bank_payment_method_diffs={self.bank_pm1.id: -20})
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details(session_ids=[session2_id])
        self.assertEqual(report['payments'][1]['money_difference'], -20)
