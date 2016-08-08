# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.account_test_classes import AccountingTestCase


class TestMrpRepair(AccountingTestCase):

    def setUp(self):
        super(TestMrpRepair, self).setUp()

        self.MrpRepair = self.env['mrp.repair']
        self.ResUsers = self.env['res.users']
        self.MrpRepairMakeInvoice = self.env['mrp.repair.make_invoice']
        self.res_group_user = self.env.ref('stock.group_stock_user')
        self.res_group_manager = self.env.ref('stock.group_stock_manager')
        self.mrp_repair_rmrp0 = self.env.ref('mrp_repair.mrp_repair_rmrp0')
        self.mrp_repair_rmrp1 = self.env.ref('mrp_repair.mrp_repair_rmrp1')
        self.mrp_repair_rmrp2 = self.env.ref('mrp_repair.mrp_repair_rmrp2')

        self.res_mrp_repair_user = self.ResUsers.create({
            'name': 'MRP User',
            'login': 'maru',
            'password': 'maru',
            'email': 'mrp_repair_user@yourcompany.com',
            'groups_id': [(6, 0, [self.res_group_user.id])]})

        self.res_mrp_repair_manager = self.ResUsers.create({
            'name': 'MRP Manager',
            'login': 'marm',
            'password': 'marm',
            'email': 'mrp_repair_manager@yourcompany.com',
            'groups_id': [(6, 0, [self.res_group_manager.id])]})

    def test_00_mrp_repair_afterinv(self):

        # I confirm Repair order taking Invoice Method 'After Repair'.
        self.mrp_repair_rmrp0.sudo(self.res_mrp_repair_user.id).action_repair_confirm()

        # I check the state is in "Confirmed".
        self.assertEqual(self.mrp_repair_rmrp0.state, "confirmed", 'Mrp repair order should be in "Confirmed" state.')
        self.mrp_repair_rmrp0.action_repair_start()

        # I check the state is in "Under Repair".
        self.assertEqual(self.mrp_repair_rmrp0.state, "under_repair", 'Mrp repair order should be in "Under_repair" state.')

        # Repairing process for product is in Done state and I end Repair process by clicking on "End Repair" button.
        self.mrp_repair_rmrp0.action_repair_end()

        # I define Invoice Method 'After Repair' option in this Repair order.so I create invoice by clicking on "Make Invoice" wizard.
        mrp_make_invoice = self.MrpRepairMakeInvoice.create({
            'group': True})

        # I click on "Create Invoice" button of this wizard to make invoice.
        context = {
            "active_model": 'mrp_repair',
            "active_ids": [self.mrp_repair_rmrp0.id],
            "active_id": self.mrp_repair_rmrp0.id
        }
        mrp_make_invoice.with_context(context).make_invoices()

        # I check that invoice is created for this Repair order.
        self.assertEqual(len(self.mrp_repair_rmrp0.invoice_id), 1, "No invoice exists for this repair order")

    def test_01_mrp_repair_b4inv(self):

        # I confirm Repair order for Invoice Method 'Before Repair'.
        self.mrp_repair_rmrp2.sudo(self.res_mrp_repair_user.id).action_repair_confirm()

        # I click on "Create Invoice" button of this wizard to make invoice.
        self.mrp_repair_rmrp2.action_repair_invoice_create()

        # I check that invoice is created for this Repair order.
        self.assertEqual(len(self.mrp_repair_rmrp2.invoice_id), 1, "No invoice exists for this repair order")

        # I start the Repairing process by clicking on "Start Repair" button.
        self.mrp_repair_rmrp2.action_repair_start()

        # Repairing process for this product is in Done state and I end this process by clicking on "End Repair" button for Invoice Method 'Before Repair'.
        self.mrp_repair_rmrp2.action_repair_end()

    def test_02_mrp_repair_noneinv(self):

        # I confirm Repair order for Invoice Method 'No Invoice'.
        self.mrp_repair_rmrp1.sudo(self.res_mrp_repair_user.id).action_repair_confirm()

        # I start the repairing process by clicking on "Start Repair" button for Invoice Method 'No Invoice'.
        self.mrp_repair_rmrp1.action_repair_start()

        # I check its state which is in "Under Repair".
        self.assertEqual(self.mrp_repair_rmrp1.state, "under_repair", 'Mrp repair order should be in "Under_repair" state.')

        # Repairing process for product is in Done state and I end this process by clicking on "End Repair" button.
        self.mrp_repair_rmrp1.action_repair_end()

        # I define Invoice Method 'No Invoice' option in this repair order.
        # So, I check that Invoice has not been created for this repair order.
        self.assertNotEqual(len(self.mrp_repair_rmrp1.invoice_id), 1, "Invoice should not exist for this repair order")

    def test_03_mrp_repair_fee(self):
        # I check the total amount of mrp_repair_rmrp1 is 100
        self.assertEqual(self.mrp_repair_rmrp1.amount_total, 100, "Amount_total should be 100")

        # I add a new fee line

        product_assembly = self.env.ref('product.product_product_5')
        product_uom_hour = self.env.ref('product.product_uom_hour')
        self.MrpRepairFee = self.env['mrp.repair.fee']

        self.MrpRepairFee.create({
            'name': 'PC Assemble + Custom (PC on Demand)',
            'product_id': product_assembly.id,
            'product_uom_qty': 1.0,
            'product_uom': product_uom_hour.id,
            'price_unit': 12.0,
            'to_invoice': True,
            'repair_id': self.mrp_repair_rmrp1.id})
        # I check the total amount of mrp_repair_rmrp1 is now 112
        self.assertEqual(self.mrp_repair_rmrp1.amount_total, 112, "Amount_total should be 100")
