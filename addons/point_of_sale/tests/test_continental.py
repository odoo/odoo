# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_anglo_saxon import TestAngloSaxonCommon


class TestContinentalCommon(TestAngloSaxonCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.anglo_saxon_accounting = False


@tagged('post_install', '-at_install')
class TestContinentalPerpetualFlow(TestContinentalCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product.write({
            'name': "Real time valo product",
            'categ_id': cls.category,
            'standard_price': 20,
            'list_price': 100
        })

    def create_pay_order_close(self):
        self.pos_config.open_ui()
        pos_session = self.pos_config.current_session_id
        pos_session.set_opening_control(0, None)

        # create order
        pos_order_values = {
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'session_id': self.pos_config.current_session_id.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product.id,
                'price_unit': 100,
                'discount': 0.0,
                'qty': 1.0,
                'price_subtotal': 100,
                'price_subtotal_incl': 100,
            })],
            'amount_total': 100,
            'amount_tax': 0,
            'amount_paid': 0,
            'amount_return': 0,
            'last_order_preparation_change': '{}'
        }

        pos_order = self.PosOrder.create(pos_order_values)

        # register payment
        context_make_payment = {"active_ids": [pos_order.id], "active_id": pos_order.id}
        pos_payment = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': 100.0,
            'payment_method_id': self.cash_payment_method.id,
        })
        context_payment = {'active_id': pos_order.id}
        pos_payment.with_context(context_payment).check()

        # validate the session
        current_session_id = self.pos_config.current_session_id
        current_session_id.post_closing_cash_details(100.0)
        current_session_id.close_session_from_ui()
        return current_session_id

    def test_inventory_valuation_session_closing_no_invoice(self):
        """ Tests that closing the session posts the stock valuation
        move line entries, even if order was not invoiced. """
        self.env.company.inventory_valuation = 'real_time'
        self.category.property_valuation = 'real_time'
        current_session_id = self.create_pay_order_close()

        valuation_account = self.category.property_stock_valuation_account_id
        valuation_lines = current_session_id.move_id.line_ids.filtered(lambda line: line.account_id == valuation_account)

        self.assertEqual(len(valuation_lines), 1)
        self.assertEqual(valuation_lines.credit, 20.0)

    def test_inventory_valuation_session_company_no_real_time(self):
        """ The inventory valuation of the product should always prevail, in this case we set
            the company to periodic valuation and check that the stock valuation move lines are still created"""
        self.env.company.inventory_valuation = 'periodic'
        self.category.property_valuation = 'real_time'
        current_session_id = self.create_pay_order_close()

        valuation_account = self.category.property_stock_valuation_account_id
        valuation_lines = current_session_id.move_id.line_ids.filtered(lambda line: line.account_id == valuation_account)

        self.assertEqual(len(valuation_lines), 1)
        self.assertEqual(valuation_lines.credit, 20.0)

    def test_inventory_valuation_session_product_no_valuation(self):
        """ If the product has no valuation, the company setting should prevail, in this case we set
            the product category valuation to false and check that the stock valuation move lines are still created"""

        self.env.company.inventory_valuation = 'real_time'
        self.category.property_valuation = False
        current_session_id = self.create_pay_order_close()

        valuation_account = self.category.property_stock_valuation_account_id
        valuation_lines = current_session_id.move_id.line_ids.filtered(lambda line: line.account_id == valuation_account)

        self.assertEqual(len(valuation_lines), 1)
        self.assertEqual(valuation_lines.credit, 20.0)
