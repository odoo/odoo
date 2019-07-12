# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

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
            'email': 'repair_user@yourcompany.com',
            'groups_id': [(6, 0, [self.res_group_user.id])]})

        self.res_repair_manager = self.ResUsers.create({
            'name': 'Repair Manager',
            'login': 'marm',
            'email': 'repair_manager@yourcompany.com',
            'groups_id': [(6, 0, [self.res_group_manager.id])]})

    def _create_simple_repair_order(self, invoice_method):
        product_to_repair = self.env.ref('product.product_product_5')
        partner = self.env.ref('base.res_partner_address_1')
        return self.env['repair.order'].create({
            'product_id': product_to_repair.id,
            'product_uom': product_to_repair.uom_id.id,
            'address_id': partner.id,
            'guarantee_limit': datetime.today().strftime('%Y-%m-%d'),
            'invoice_method': invoice_method,
            'partner_invoice_id': partner.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'partner_id': self.env.ref('base.res_partner_12').id
        })

    def _create_simple_operation(self, repair_id=False, qty=0.0, price_unit=0.0):
        product_to_add = self.env.ref('product.product_product_5')
        return self.env['repair.line'].create({
            'name': 'Add The product',
            'type': 'add',
            'product_id': product_to_add.id,
            'product_uom_qty': qty,
            'product_uom': product_to_add.uom_id.id,
            'price_unit': price_unit,
            'repair_id': repair_id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': product_to_add.property_stock_production.id,
        })

    def _create_simple_fee(self, repair_id=False, qty=0.0, price_unit=0.0):
        product_service = self.env.ref('product.product_product_2')
        return self.env['repair.fee'].create({
            'name': 'PC Assemble + Custom (PC on Demand)',
            'product_id': product_service.id,
            'product_uom_qty': qty,
            'product_uom': product_service.uom_id.id,
            'price_unit': price_unit,
            'repair_id': repair_id,
        })

    def test_00_repair_afterinv(self):
        repair = self._create_simple_repair_order('after_repair')
        self._create_simple_operation(repair_id=repair.id, qty=1.0, price_unit=50.0)
        # I confirm Repair order taking Invoice Method 'After Repair'.
        repair.with_user(self.res_repair_user).action_repair_confirm()

        # I check the state is in "Confirmed".
        self.assertEqual(repair.state, "confirmed", 'Repair order should be in "Confirmed" state.')
        repair.action_repair_start()

        # I check the state is in "Under Repair".
        self.assertEqual(repair.state, "under_repair", 'Repair order should be in "Under_repair" state.')

        # Repairing process for product is in Done state and I end Repair process by clicking on "End Repair" button.
        repair.action_repair_end()

        # I define Invoice Method 'After Repair' option in this Repair order.so I create invoice by clicking on "Make Invoice" wizard.
        make_invoice = self.RepairMakeInvoice.create({
            'group': True})
        # I click on "Create Invoice" button of this wizard to make invoice.
        context = {
            "active_model": 'repair_order',
            "active_ids": [repair.id],
            "active_id": repair.id
        }
        make_invoice.with_context(context).make_invoices()

        # I check that invoice is created for this Repair order.
        self.assertEqual(len(repair.invoice_id), 1, "No invoice exists for this repair order")
        self.assertEqual(len(repair.move_id.move_line_ids[0].consume_line_ids), 1, "Consume lines should be set")

    def test_01_repair_b4inv(self):
        repair = self._create_simple_repair_order('b4repair')
        # I confirm Repair order for Invoice Method 'Before Repair'.
        repair.with_user(self.res_repair_user).action_repair_confirm()

        # I click on "Create Invoice" button of this wizard to make invoice.
        repair.action_repair_invoice_create()

        # I check that invoice is created for this Repair order.
        self.assertEqual(len(repair.invoice_id), 1, "No invoice exists for this repair order")

    def test_02_repair_noneinv(self):
        repair = self._create_simple_repair_order('none')

        # Add a new fee line
        self._create_simple_fee(repair_id=repair.id, qty=1.0, price_unit=12.0)

        self.assertEqual(repair.amount_total, 12, "Amount_total should be 12")
        # Add new operation line
        self._create_simple_operation(repair_id=repair.id, qty=1.0, price_unit=14.0)

        self.assertEqual(repair.amount_total, 26, "Amount_total should be 26")

        # I confirm Repair order for Invoice Method 'No Invoice'.
        repair.with_user(self.res_repair_user).action_repair_confirm()

        # I start the repairing process by clicking on "Start Repair" button for Invoice Method 'No Invoice'.
        repair.action_repair_start()

        # I check its state which is in "Under Repair".
        self.assertEqual(repair.state, "under_repair", 'Repair order should be in "Under_repair" state.')

        # Repairing process for product is in Done state and I end this process by clicking on "End Repair" button.
        repair.action_repair_end()

        self.assertEqual(repair.move_id.location_id.id, self.env.ref('stock.stock_location_stock').id,
                         'Repaired product was taken in the wrong location')
        self.assertEqual(repair.move_id.location_dest_id.id, self.env.ref('stock.stock_location_stock').id,
                         'Repaired product went to the wrong location')
        self.assertEqual(repair.operations.move_id.location_id.id, self.env.ref('stock.stock_location_stock').id,
                         'Consumed product was taken in the wrong location')
        self.assertEqual(repair.operations.move_id.location_dest_id.id, self.env.ref('product.product_product_5').property_stock_production.id,
                         'Consumed product went to the wrong location')

        # I define Invoice Method 'No Invoice' option in this repair order.
        # So, I check that Invoice has not been created for this repair order.
        self.assertNotEqual(len(repair.invoice_id), 1, "Invoice should not exist for this repair order")
