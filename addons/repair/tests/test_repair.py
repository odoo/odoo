# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestRepair(AccountingTestCase):

    def setUp(self):
        super(TestRepair, self).setUp()

        self.Repair = self.env['repair.order']
        self.ResUsers = self.env['res.users']
        self.RepairMakeInvoice = self.env['repair.order.make_invoice']
        self.res_group_user = self.env.ref('stock.group_stock_user')
        self.res_group_manager = self.env.ref('stock.group_stock_manager')
        self.repair_r0 = self.env.ref('repair.repair_r0')
        self.repair_r1 = self.env.ref('repair.repair_r1')
        self.repair_r2 = self.env.ref('repair.repair_r2')

        self.res_repair_user = self.ResUsers.create({
            'name': 'Repair User',
            'login': 'maru',
            'password': 'maru',
            'email': 'repair_user@yourcompany.com',
            'groups_id': [(6, 0, [self.res_group_user.id])]})

        self.res_repair_manager = self.ResUsers.create({
            'name': 'Repair Manager',
            'login': 'marm',
            'password': 'marm',
            'email': 'repair_manager@yourcompany.com',
            'groups_id': [(6, 0, [self.res_group_manager.id])]})

    def test_00_repair_afterinv(self):

        # I confirm Repair order taking Invoice Method 'After Repair'.
        self.repair_r0.sudo(self.res_repair_user.id).action_repair_confirm()

        # I check the state is in "Confirmed".
        self.assertEqual(self.repair_r0.state, "confirmed", 'Repair order should be in "Confirmed" state.')
        self.repair_r0.action_repair_start()

        # I check the state is in "Under Repair".
        self.assertEqual(self.repair_r0.state, "under_repair", 'Repair order should be in "Under_repair" state.')

        # Repairing process for product is in Done state and I end Repair process by clicking on "End Repair" button.
        self.repair_r0.action_repair_end()

        # I define Invoice Method 'After Repair' option in this Repair order.so I create invoice by clicking on "Make Invoice" wizard.
        make_invoice = self.RepairMakeInvoice.create({
            'group': True})
        # I click on "Create Invoice" button of this wizard to make invoice.
        context = {
            "active_model": 'repair_order',
            "active_ids": [self.repair_r0.id],
            "active_id": self.repair_r0.id
        }
        make_invoice.with_context(context).make_invoices()

        # I check that invoice is created for this Repair order.
        self.assertEqual(len(self.repair_r0.invoice_id), 1, "No invoice exists for this repair order")
        self.assertEqual(len(self.repair_r0.move_id.move_line_ids[0].consume_line_ids), 1, "Consume lines should be set")

    def test_01_epair_b4inv(self):

        # I confirm Repair order for Invoice Method 'Before Repair'.
        self.repair_r2.sudo(self.res_repair_user.id).action_repair_confirm()

        # I click on "Create Invoice" button of this wizard to make invoice.
        self.repair_r2.action_repair_invoice_create()

        # I check that invoice is created for this Repair order.
        self.assertEqual(len(self.repair_r2.invoice_id), 1, "No invoice exists for this repair order")

        # I start the Repairing process by clicking on "Start Repair" button.
        self.repair_r2.action_repair_start()

        # Repairing process for this product is in Done state and I end this process by clicking on "End Repair" button for Invoice Method 'Before Repair'.
        self.repair_r2.action_repair_end()

    def test_02_repair_noneinv(self):

        # I confirm Repair order for Invoice Method 'No Invoice'.
        self.repair_r1.sudo(self.res_repair_user.id).action_repair_confirm()

        # I start the repairing process by clicking on "Start Repair" button for Invoice Method 'No Invoice'.
        self.repair_r1.action_repair_start()

        # I check its state which is in "Under Repair".
        self.assertEqual(self.repair_r1.state, "under_repair", 'Repair order should be in "Under_repair" state.')

        # Repairing process for product is in Done state and I end this process by clicking on "End Repair" button.
        self.repair_r1.action_repair_end()

        # I define Invoice Method 'No Invoice' option in this repair order.
        # So, I check that Invoice has not been created for this repair order.
        self.assertNotEqual(len(self.repair_r1.invoice_id), 1, "Invoice should not exist for this repair order")

    def test_03_repair_fee(self):
        # I check the total amount of repair_r1 is 100
        self.assertEqual(self.repair_r1.amount_total, 100, "Amount_total should be 100")

        # I add a new fee line

        product_assembly = self.env.ref('product.product_product_5')
        product_uom_hour = self.env.ref('product.product_uom_hour')
        self.RepairFee = self.env['repair.fee']

        self.RepairFee.create({
            'name': 'PC Assemble + Custom (PC on Demand)',
            'product_id': product_assembly.id,
            'product_uom_qty': 1.0,
            'product_uom': product_uom_hour.id,
            'price_unit': 12.0,
            'repair_id': self.repair_r1.id})
        # I check the total amount of repair_r1 is now 112
        self.assertEqual(self.repair_r1.amount_total, 112, "Amount_total should be 100")
