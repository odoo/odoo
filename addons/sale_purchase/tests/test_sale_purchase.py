# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, AccessError

from odoo.addons.sale_purchase.tests.common import TestCommonSalePurchaseNoChart


class TestSalePurchase(TestCommonSalePurchaseNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestSalePurchase, cls).setUpClass()

        # set up users
        cls.setUpUsers()
        group_salemanager = cls.env.ref('sales_team.group_sale_manager')
        group_salesman = cls.env.ref('sales_team.group_sale_salesman')
        cls.user_manager.write({'groups_id': [(6, 0, [group_salemanager.id])]})
        cls.user_employee.write({'groups_id': [(6, 0, [group_salesman.id])]})

        # set up accounts and products and journals
        cls.setUpAdditionalAccounts()
        cls.setUpAccountJournal()
        cls.setUpClassicProducts()
        cls.setUpServicePurchaseProducts()

        # create a generic Sale Order with 2 classical products and a purchase service
        SaleOrder = cls.env['sale.order'].with_context(tracking_disable=True)
        cls.sale_order_1 = SaleOrder.create({
            'partner_id': cls.partner_customer_usd.id,
            'partner_invoice_id': cls.partner_customer_usd.id,
            'partner_shipping_id': cls.partner_customer_usd.id,
            'pricelist_id': cls.pricelist_usd.id,
        })
        cls.sol1_service_deliver = cls.env['sale.order.line'].create({
            'name': cls.service_deliver.name,
            'product_id': cls.service_deliver.id,
            'product_uom_qty': 1,
            'product_uom': cls.service_deliver.uom_id.id,
            'price_unit': cls.service_deliver.list_price,
            'order_id': cls.sale_order_1.id,
            'tax_id': False,
        })
        cls.sol1_product_order = cls.env['sale.order.line'].create({
            'name': cls.product_order.name,
            'product_id': cls.product_order.id,
            'product_uom_qty': 2,
            'product_uom': cls.product_order.uom_id.id,
            'price_unit': cls.product_order.list_price,
            'order_id': cls.sale_order_1.id,
            'tax_id': False,
        })
        cls.sol1_service_purchase_1 = cls.env['sale.order.line'].create({
            'name': cls.service_purchase_1.name,
            'product_id': cls.service_purchase_1.id,
            'product_uom_qty': 4,
            'product_uom': cls.service_purchase_1.uom_id.id,
            'price_unit': cls.service_purchase_1.list_price,
            'order_id': cls.sale_order_1.id,
            'tax_id': False,
        })

        cls.sale_order_2 = SaleOrder.create({
            'partner_id': cls.partner_customer_usd.id,
            'partner_invoice_id': cls.partner_customer_usd.id,
            'partner_shipping_id': cls.partner_customer_usd.id,
            'pricelist_id': cls.pricelist_usd.id,
        })
        cls.sol2_product_deliver = cls.env['sale.order.line'].create({
            'name': cls.product_deliver.name,
            'product_id': cls.product_deliver.id,
            'product_uom_qty': 5,
            'product_uom': cls.product_deliver.uom_id.id,
            'price_unit': cls.product_deliver.list_price,
            'order_id': cls.sale_order_2.id,
            'tax_id': False,
        })
        cls.sol2_service_order = cls.env['sale.order.line'].create({
            'name': cls.service_order.name,
            'product_id': cls.service_order.id,
            'product_uom_qty': 6,
            'product_uom': cls.service_order.uom_id.id,
            'price_unit': cls.service_order.list_price,
            'order_id': cls.sale_order_2.id,
            'tax_id': False,
        })
        cls.sol2_service_purchase_2 = cls.env['sale.order.line'].create({
            'name': cls.service_purchase_2.name,
            'product_id': cls.service_purchase_2.id,
            'product_uom_qty': 7,
            'product_uom': cls.service_purchase_2.uom_id.id,
            'price_unit': cls.service_purchase_2.list_price,
            'order_id': cls.sale_order_2.id,
            'tax_id': False,
        })

    def test_sale_create_purchase(self):
        """ Confirming 2 sales orders with a service that should create a PO, then cancelling the PO should shedule 1 next activity per SO """
        self.sale_order_1.action_confirm()
        self.sale_order_2.action_confirm()

        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.supplierinfo1.name.id), ('state', '=', 'draft')])
        purchase_lines_so1 = self.env['purchase.order.line'].search([('sale_line_id', 'in', self.sale_order_1.order_line.ids)])
        purchase_line1 = purchase_lines_so1[0]

        purchase_lines_so2 = self.env['purchase.order.line'].search([('sale_line_id', 'in', self.sale_order_2.order_line.ids)])
        purchase_line2 = purchase_lines_so2[0]

        self.assertEqual(len(purchase_order), 1, "Only one PO should have been created, from the 2 Sales orders")
        self.assertEqual(len(purchase_order.order_line), 2, "The purchase order should have 2 lines")
        self.assertEqual(len(purchase_lines_so1), 1, "Only one SO line from SO 1 should have create a PO line")
        self.assertEqual(len(purchase_lines_so2), 1, "Only one SO line from SO 2 should have create a PO line")
        self.assertEqual(len(purchase_order.activity_ids), 0, "No activity should be scheduled on the PO")
        self.assertEqual(purchase_order.state, 'draft', "The created PO should be in draft state")

        self.assertNotEqual(purchase_line1.product_id, purchase_line2.product_id, "The 2 PO line should have different products")
        self.assertEqual(purchase_line1.product_id, self.sol1_service_purchase_1.product_id, "The create PO line must have the same product as its mother SO line")
        self.assertEqual(purchase_line2.product_id, self.sol2_service_purchase_2.product_id, "The create PO line must have the same product as its mother SO line")

        purchase_order.button_cancel()

        self.assertEqual(len(self.sale_order_1.activity_ids), 1, "One activity should be scheduled on the SO 1 since the PO has been cancelled")
        self.assertEqual(self.sale_order_1.user_id, self.sale_order_1.activity_ids[0].user_id, "The activity should be assigned to the SO responsible")

        self.assertEqual(len(self.sale_order_2.activity_ids), 1, "One activity should be scheduled on the SO 2 since the PO has been cancelled")
        self.assertEqual(self.sale_order_2.user_id, self.sale_order_2.activity_ids[0].user_id, "The activity should be assigned to the SO responsible")

    def test_uom_conversion(self):
        """ Test generated PO use the right UoM according to product configuration """
        self.sale_order_2.action_confirm()
        purchase_line = self.env['purchase.order.line'].search([('sale_line_id', '=', self.sol2_service_purchase_2.id)])  # only one line

        self.assertTrue(purchase_line, "The SO line should generate a PO line")
        self.assertEqual(purchase_line.product_uom, self.service_purchase_2.uom_po_id, "The UoM on the purchase line should be the one from the product configuration")
        self.assertNotEqual(purchase_line.product_uom, self.sol2_service_purchase_2.product_uom, "As the product configuration, the UoM on the SO line should still be different from the one on the PO line")
        self.assertEqual(purchase_line.product_qty, self.sol2_service_purchase_2.product_uom_qty * 12, "The quantity from the SO should be converted with th UoM factor on the PO line")

    def test_no_supplier(self):
        """ Test confirming SO with product with no supplier raise Error """
        # delete the suppliers
        self.supplierinfo1.unlink()
        # confirm the SO should raise UserError
        with self.assertRaises(UserError):
            self.sale_order_1.action_confirm()

    def test_reconfirm_sale_order(self):
        """ Confirm SO, cancel it, then re-confirm it should not regenerate a purchase line """
        self.sale_order_1.action_confirm()

        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.supplierinfo1.name.id), ('state', '=', 'draft')])
        purchase_lines = self.env['purchase.order.line'].search([('sale_line_id', 'in', self.sale_order_1.order_line.ids)])
        purchase_line = purchase_lines[0]

        self.assertEqual(len(purchase_lines), 1, "Only one purchase line should be created on SO confirmation")
        self.assertEqual(len(purchase_order), 1, "One purchase order should have been created on SO confirmation")
        self.assertEqual(len(purchase_order.order_line), 1, "Only one line on PO, after SO confirmation")
        self.assertEqual(purchase_order, purchase_lines.order_id, "The generated purchase line should be in the generated purchase order")
        self.assertEqual(purchase_order.state, 'draft', "Generated purchase should be in draft state")
        self.assertEqual(purchase_line.price_unit, self.supplierinfo1.price, "Purchase line price is the one from the supplier")
        self.assertEqual(purchase_line.product_qty, self.sol1_service_purchase_1.product_uom_qty, "Quantity on SO line is not the same on the purchase line (same UoM)")

        self.sale_order_1.action_cancel()

        self.assertEqual(len(purchase_order.activity_ids), 1, "One activity should be scheduled on the PO since a SO has been cancelled")

        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.supplierinfo1.name.id), ('state', '=', 'draft')])
        purchase_lines = self.env['purchase.order.line'].search([('sale_line_id', 'in', self.sale_order_1.order_line.ids)])
        purchase_line = purchase_lines[0]

        self.assertEqual(len(purchase_lines), 1, "Always one purchase line even after SO cancellation")
        self.assertTrue(purchase_order, "Always one purchase order even after SO cancellation")
        self.assertEqual(len(purchase_order.order_line), 1, "Still one line on PO, even after SO cancellation")
        self.assertEqual(purchase_order, purchase_lines.order_id, "The generated purchase line should still be in the generated purchase order")
        self.assertEqual(purchase_order.state, 'draft', "Generated purchase should still be in draft state")
        self.assertEqual(purchase_line.price_unit, self.supplierinfo1.price, "Purchase line price is still the one from the supplier")
        self.assertEqual(purchase_line.product_qty, self.sol1_service_purchase_1.product_uom_qty, "Quantity on SO line should still be the same on the purchase line (same UoM)")

        self.sale_order_1.action_draft()
        self.sale_order_1.action_confirm()

        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.supplierinfo1.name.id), ('state', '=', 'draft')])
        purchase_lines = self.env['purchase.order.line'].search([('sale_line_id', 'in', self.sale_order_1.order_line.ids)])
        purchase_line = purchase_lines[0]

        self.assertEqual(len(purchase_lines), 1, "Still only one purchase line should be created even after SO reconfirmation")
        self.assertEqual(len(purchase_order), 1, "Still one purchase order should be after SO reconfirmation")
        self.assertEqual(len(purchase_order.order_line), 1, "Only one line on PO, even after SO reconfirmation")
        self.assertEqual(purchase_order, purchase_lines.order_id, "The generated purchase line should be in the generated purchase order")
        self.assertEqual(purchase_order.state, 'draft', "Generated purchase should be in draft state")
        self.assertEqual(purchase_line.price_unit, self.supplierinfo1.price, "Purchase line price is the one from the supplier")
        self.assertEqual(purchase_line.product_qty, self.sol1_service_purchase_1.product_uom_qty, "Quantity on SO line is not the same on the purchase line (same UoM)")

    def test_update_ordered_sale_quantity(self):
        """ Test the purchase order behovior when changing the ordered quantity on the sale order line.
            Increase of qty on the SO
            - If PO is draft ['draft', 'sent', 'to approve'] : increase the quantity on the PO
            - If PO is confirmed ['purchase', 'done', 'cancel'] : create a new PO

            Decrease of qty on the SO
            - If PO is draft  ['draft', 'sent', 'to approve'] : next activity on the PO
            - If PO is confirmed ['purchase', 'done', 'cancel'] : next activity on the PO
        """
        self.sale_order_1.action_confirm()

        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.supplierinfo1.name.id), ('state', '=', 'draft')])
        purchase_lines = self.env['purchase.order.line'].search([('sale_line_id', 'in', self.sale_order_1.order_line.ids)])
        purchase_line = purchase_lines[0]

        self.assertEqual(purchase_order.state, 'draft', "The created purchase should be in draft state")
        self.assertFalse(purchase_order.activity_ids, "There is no activities on the PO")
        self.assertEqual(purchase_line.product_qty, self.sol1_service_purchase_1.product_uom_qty, "Quantity on SO line is not the same on the purchase line (same UoM)")

        # increase the ordered quantity on sale line
        self.sol1_service_purchase_1.write({'product_uom_qty': self.sol1_service_purchase_1.product_uom_qty + 12})  # product_uom_qty = 16
        self.assertEqual(purchase_line.product_qty, self.sol1_service_purchase_1.product_uom_qty, "The quantity of draft PO line should be increased as the one from the sale line changed")

        sale_line_old_quantity = self.sol1_service_purchase_1.product_uom_qty

        # decrease the ordered quantity on sale line
        self.sol1_service_purchase_1.write({'product_uom_qty': self.sol1_service_purchase_1.product_uom_qty - 3})  # product_uom_qty = 13
        self.assertEqual(len(purchase_order.activity_ids), 1, "One activity should have been created on the PO")
        self.assertEqual(purchase_order.activity_ids.user_id, purchase_order.user_id, "Activity assigned to PO responsible")
        self.assertEqual(purchase_order.activity_ids.state, 'today', "Activity is for today, as it is urgent")

        # confirm the PO
        purchase_order.button_confirm()

        # decrease the ordered quantity on sale line
        self.sol1_service_purchase_1.write({'product_uom_qty': self.sol1_service_purchase_1.product_uom_qty - 5})  # product_uom_qty = 8

        purchase_order.invalidate_cache()  # Note: creating a second activity will not refresh the cache

        self.assertEqual(purchase_line.product_qty, sale_line_old_quantity, "The quantity on the PO line should not have changed.")
        self.assertEqual(len(purchase_order.activity_ids), 2, "a second activity should have been created on the PO")
        self.assertEqual(purchase_order.activity_ids.mapped('user_id'), purchase_order.user_id, "Activities assigned to PO responsible")
        self.assertEqual(purchase_order.activity_ids.mapped('state'), ['today', 'today'], "Activities are for today, as it is urgent")

        # increase the ordered quantity on sale line
        delta = 8
        self.sol1_service_purchase_1.write({'product_uom_qty': self.sol1_service_purchase_1.product_uom_qty + delta})  # product_uom_qty = 16

        self.assertEqual(purchase_line.product_qty, sale_line_old_quantity, "The quantity on the PO line should not have changed.")
        self.assertEqual(len(purchase_order.activity_ids), 2, "Always 2 activity on confirmed the PO")

        purchase_order2 = self.env['purchase.order'].search([('partner_id', '=', self.supplierinfo1.name.id), ('state', '=', 'draft')])
        purchase_lines = self.env['purchase.order.line'].search([('sale_line_id', 'in', self.sale_order_1.order_line.ids)])
        purchase_lines2 = purchase_lines.filtered(lambda pol: pol.order_id == purchase_order2)
        purchase_line2 = purchase_lines2[0]

        self.assertTrue(purchase_order2, "A second PO is created by increasing sale quantity when first PO is confirmed")
        self.assertEqual(purchase_order2.state, 'draft', "The second PO is in draft state")
        self.assertNotEqual(purchase_order, purchase_order2, "The 2 PO are different")
        self.assertEqual(len(purchase_lines), 2, "The same Sale Line has created 2 purchase lines")
        self.assertEqual(len(purchase_order2.order_line), 1, "The 2nd PO has only one line")
        self.assertEqual(purchase_line2.sale_line_id, self.sol1_service_purchase_1, "The 2nd PO line came from the SO line sol1_service_purchase_1")
        self.assertEqual(purchase_line2.product_qty, delta, "The quantity of the new PO line is the quantity added on the Sale Line, after first PO confirmation")
