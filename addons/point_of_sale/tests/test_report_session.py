# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo

from odoo.addons.point_of_sale.tests.common import TestPoSCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestReportSession(TestPoSCommon):

    _test_user_groups = None  # FIXME list needed groups

    def setUp(self):
        super(TestReportSession, self).setUp()
        self.config = self.basic_config

    def test_report_listing(self):
        product1 = self.create_product('Product 1', self.categ_basic, 150)
        product2 = self.create_product('Product 2', self.categ_basic, 150)

        cash_payment_method = self.env['pos.payment.method'].create({
            'name': 'Cash',
            'type': 'cash',
            'receivable_account_id': self.company_data['default_account_receivable'].id,
            'journal_id': self.company_data['default_journal_cash'].id,
            'company_id': self.env.company.id,
        })
        bank_payment_method = self.env['pos.payment.method'].create({
            'name': 'Bank',
            'type': 'bank',
            'journal_id': self.company_data['default_journal_bank'].id,
            'receivable_account_id': self.company_data['default_account_receivable'].id,
            'company_id': self.env.company.id,
        })
        self.config.write({'payment_method_ids': [(5, 0), (4, bank_payment_method.id), (4, cash_payment_method.id)]})

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
