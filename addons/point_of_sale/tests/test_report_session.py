# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo

from odoo.addons.point_of_sale.tests.common import TestPoSCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestReportSession(TestPoSCommon):

    def setUp(self):
        super(TestReportSession, self).setUp()
        self.config = self.basic_config

    def test_report_session(self):

        product1 = self.create_product('Product 1', self.categ_basic, 150)
        self.open_new_session()
        session = self.pos_session

        order = self.env['pos.order'].create({
            'session_id': session.id,
            'partner_id': self.partner_a.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': product1.id,
                'price_unit': 150,
                'discount': 0,
                'qty': 1.0,
                'price_subtotal': 150,
                'price_subtotal_incl': 150,
            }),],
            'amount_total': 150.0,
            'amount_tax': 0.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'last_order_preparation_change': '{}'
        })

        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': 150,
            'payment_method_id': self.bank_split_pm1.id
        })
        order_payment.with_context(**payment_context).check()
        session.action_pos_session_closing_control(bank_payment_method_diffs={self.bank_split_pm1.id: 50})

        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details(session_ids=[session.id])
        split_payment_bank = [p for p in report['payments'] if p.get('id', 0) == self.bank_split_pm1.id]
        self.assertEqual(split_payment_bank[0]['cash_moves'][0]['amount'], 50)
