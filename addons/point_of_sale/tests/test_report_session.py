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
            'price_include': True,
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
        self.assertEqual(bank_payment[0]['cash_moves'][0]['amount'], 40)
        self.assertEqual(report['products_info']['total'], 100, "Total amount of products should be 100, as we want total without tax")
        self.assertEqual(report['products'][0]['products'][0]['base_amount'], 100, "Base amount of product should be 100, as we want price without tax")
