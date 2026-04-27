# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.point_of_sale.models.pos_config import PosConfig
from unittest.mock import patch
from odoo import Command


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(TestPointOfSaleHttpCommon):
    def test_settle_account_due_update_instantly(self):
        self.partner_test_a = self.env["res.partner"].create({"name": "A Partner"})
        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })

        self.main_pos_config.write({'payment_method_ids': [(6, 0, self.customer_account_payment_method.ids)]})
        self.main_pos_config.open_ui()
        self.assertEqual(self.partner_test_a.has_moves, False)
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'pos_settle_account_due_update_instantly', login="accountman")
        self.main_pos_config.current_session_id.action_pos_session_closing_control()
        self.assertEqual(self.partner_test_a.has_moves, True)

    def test_settle_due_account_ui_coherency(self):
        """
        Test that an invoice can be created after the session is closed
        Also that the button changes text depending on the current due amount.
        And that the receipt does not have a misleading empty state.
        """
        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })
        self.partner_test_a = self.env["res.partner"].create({"name": "A Partner"})
        self.partner_test_b = self.env["res.partner"].create({"name": "B Partner"})

        self.main_pos_config.write({'payment_method_ids': [(4, self.customer_account_payment_method.id)]})

        self.main_pos_config.open_ui()
        current_session = self.main_pos_config.current_session_id

        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner_test_b.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product_a.id,
                'price_unit': 1000,
                'discount': 0,
                'qty': 1,
                'tax_ids': [[6, False, []]],
                'price_subtotal': 1000,
                'price_subtotal_incl': 1000,
            })],
            'pricelist_id': self.main_pos_config.pricelist_id.id,
            'amount_paid': 1000.0,
            'amount_total': 1000.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
        })

        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': 1000.0,
            'payment_method_id': self.customer_account_payment_method.id
        })
        order_payment.with_context(**payment_context).check()
        current_session.close_session_from_ui()
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'SettleDueUICoherency', login="accountman")

        self.main_pos_config.current_session_id.close_session_from_ui()
        self.main_pos_config.write({'payment_method_ids': [(3, self.customer_account_payment_method.id)]})
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_settle_due_account_ui_coherency_2', login="accountman")

    def test_settle_due_search_more(self):
        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })
        partner_test_a = self.env["res.partner"].create({"name": "APartner"})
        partner_test_b = self.env["res.partner"].create({"name": "BPartner"})

        def mocked_get_limited_partners_loading(self):
            return [(partner_test_a.id,)]

        payment_methods = self.main_pos_config.payment_method_ids | self.customer_account_payment_method
        self.main_pos_config.write({'payment_method_ids': [Command.set(payment_methods.ids)]})

        self.assertEqual(partner_test_b.total_due, 0)

        self.main_pos_config.with_user(self.pos_admin).open_ui()
        current_session = self.main_pos_config.current_session_id

        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': partner_test_b.id,
            'lines': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 10,
                'discount': 0,
                'qty': 1,
                'price_subtotal': 10,
                'price_subtotal_incl': 10,
            })],
            'amount_paid': 10.0,
            'amount_total': 10.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': True,
            'last_order_preparation_change': '{}'
        })

        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': 10.0,
            'payment_method_id': self.customer_account_payment_method.id
        })
        order_payment.with_context(**payment_context).check()

        self.assertEqual(partner_test_b.total_due, 10)
        current_session.action_pos_session_closing_control()

        self.main_pos_config.with_user(self.user).open_ui()
        with patch.object(PosConfig, 'get_limited_partners_loading', mocked_get_limited_partners_loading):
            self.main_pos_config.open_ui()
            self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'SettleDueAmountMoreCustomers', login="pos_user")

    def test_settle_account_due_aml_reconcile(self):
        self.partner_test_a = self.env["res.partner"].create({"name": "A Partner"})
        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })
        payment_methods = self.main_pos_config.payment_method_ids | self.customer_account_payment_method
        self.main_pos_config.write({'payment_method_ids': [Command.set(payment_methods.ids)]})
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_settle_account_due_aml_reconcile', login="accountman")
        self.main_pos_config.current_session_id.close_session_from_ui()
        self.assertEqual(self.partner_test_a.total_due, 0)
        self.assertEqual(len(self.partner_test_a.unreconciled_aml_ids), 0)

    def test_deposit_shown_partner_list(self):
        """
        Test that an invoice can be created after the session is closed
        Also that the button changes text depending on the current due amount.
        And that the receipt does not have a misleading empty state.
        """
        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })
        payment_methods = self.main_pos_config.payment_method_ids | self.customer_account_payment_method
        self.main_pos_config.write({'payment_method_ids': [Command.set(payment_methods.ids)]})
        self.partner_test_a = self.env["res.partner"].create({"name": "AAA Partner"})
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_deposit_shown_partner_list', login="accountman")

    def test_pos_settling_account_resets_on_payment_screen_unmount(self):
        """
        Test that the variable is_settling_account resets to false
        if payment is not completed or user returns back to product screen
        """
        self.main_pos_config.open_ui()
        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            'test_pos_settling_account_resets_on_payment_screen_unmount',
            login="accountman"
        )
