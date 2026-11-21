# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo
from odoo.fields import Command

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

    def test_report_bank_difference_per_payment_method(self):
        """Each bank payment method must only show its own closing difference."""
        product = self.create_product('Product A', self.categ_basic, 100)
        report = self.env.ref('point_of_sale.pos_sales_detail_report')

        def create_paid_order(session, payments):
            order = self.env['pos.order'].create({
                'company_id': self.env.company.id,
                'session_id': session.id,
                'partner_id': self.partner_a.id,
                'lines': [Command.create({
                    'name': "OL/0001",
                    'product_id': product.id,
                    'price_unit': 100,
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
            })
            for pm, amount in payments:
                self.make_payment(order, pm, amount)

        def get_differences(session):
            lines = report.get_unfold_data({'session_id': session.id}, 'session_control')['lines']
            return {
                pm.id: line['values']['difference']
                for line in lines
                for pm in (self.bank_pm1, self.bank_split_pm1)
                if line['record_id'] == f'{session.id}_{pm.id}'
            }

        # Both bank payment methods have a closing difference
        self.config.open_ui()
        session = self.config.current_session_id
        create_paid_order(session, [(self.bank_pm1, 60), (self.bank_split_pm1, 40)])
        session.close_session_from_ui(payment_method_closing={self.bank_pm1.id: 40, self.bank_split_pm1.id: 30})
        self.assertEqual(len(session.correction_move_ids), 2)
        self.assertEqual(get_differences(session), {self.bank_pm1.id: -20, self.bank_split_pm1.id: -10})

        # Only one bank payment method has a closing difference
        self.config.open_ui()
        session = self.config.current_session_id
        create_paid_order(session, [(self.bank_pm1, 60), (self.bank_split_pm1, 40)])
        session.close_session_from_ui(payment_method_closing={self.bank_pm1.id: 40, self.bank_split_pm1.id: 40})
        self.assertEqual(len(session.correction_move_ids), 1)
        self.assertEqual(get_differences(session), {self.bank_pm1.id: -20, self.bank_split_pm1.id: 0})

        # The session is closed in another language than the report
        self.env['res.lang']._activate_lang('fr_FR')
        self.bank_pm1.update_field_translations('name', {'fr_FR': 'Banque'})
        self.bank_split_pm1.update_field_translations('name', {'fr_FR': 'Banque fractionnée'})
        self.config.open_ui()
        session = self.config.current_session_id
        create_paid_order(session, [(self.bank_pm1, 60), (self.bank_split_pm1, 40)])
        session.with_context(lang='fr_FR').close_session_from_ui(
            payment_method_closing={self.bank_pm1.id: 40, self.bank_split_pm1.id: 30})
        self.assertEqual(set(session.correction_move_ids.line_ids.mapped('name')), {'Banque', 'Banque fractionnée'})
        self.assertEqual(get_differences(session), {self.bank_pm1.id: -20, self.bank_split_pm1.id: -10})
