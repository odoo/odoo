from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged, Form
from odoo.tools import float_compare, float_is_zero
from odoo.addons.repair.tests.test_repair import TestRepair


@tagged('post_install', '-at_install')
class TestRepairSale(TestRepair):

    def test_stock_user_can_read_repair_order_without_invoicing_rights(self):
        """A user with only Inventory/User rights must be able to open a repair
        order even though they have no access to account.move."""
        stock_user = self.env['res.users'].create({
            'name': 'Stock User',
            'login': 'repair_stock_user',
            'group_ids': [Command.set([self.env.ref('stock.group_stock_user').id])],
        })
        self.repair0.invalidate_recordset()
        self.repair0.with_user(stock_user).read(['invoice_count', 'can_create_sale_or_invoice'])

    def test_create_quotation_from_repair(self):
        repair = self._create_simple_repair_order()
        lineA = self._create_simple_part_move(repair.id, 1.0, self.product_storable_no)
        repair.move_ids |= lineA
        repair.product_id = self.product_storable_serial
        repair.action_validate()
        # Create quotation
        # No partner warning -> working case -> already linked warning
        # Ensure SO doesn't exist
        self.assertEqual(len(repair.sale_order_id), 0)
        repair.partner_id = None
        with self.assertRaises(UserError) as err:
            repair.action_create_sale_order()
        self.assertIn("You need to define a customer", err.exception.args[0])
        repair.partner_id = self.res_partner_12.id
        repair.action_create_sale_order()
        # Ensure SO and SOL were created
        self.assertTrue(repair.sale_order_id)
        self.assertEqual(len(repair.sale_order_id.order_line), 1)
        with self.assertRaises(UserError) as err:
            repair.action_create_sale_order()
        self.assertNotEqual(repair.state, "done")
        repair.action_repair_cancel()
        self.assertEqual(repair.state, "cancel")
        self.assertTrue(all(m.state == "cancel" for m in repair.move_ids))
        self.assertTrue(all(float_is_zero(sol.product_uom_qty, 2) for sol in repair.sale_order_line_id))

    def test_02_repair_sale_order_binding(self):
        # Binding from SO to RO(s)
        #   On SO Confirm
        #     - Create linked RO per line (only if service_tracking == 'repair')
        #   Create Repair SOL
        #     - sol qty updated to 0 -> RO canceled (Reciprocal is true too)
        #     - sol qty back to >0 -> RO Confirmed (Reciprocal is not true)
        #   RO Parts SOL
        #     - SOL qty change is NOT propagated to RO
        #     - However, these changes FROM RO are propagated to SO
        # ----------------------------------------------------------------------------------
        #  Binding from RO to SO
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.res_partner_1
        with so_form.order_line.new() as line:
            line.product_id = self.product_order_repair
            line.product_uom_qty = 2.0
        with so_form.order_line.new() as line:
            line.display_type = 'line_section'
            line.name = 'Dummy Section'
        sale_order = so_form.save()
        order_line = sale_order.order_line[0]
        line_section = sale_order.order_line[1]
        self.assertEqual(len(sale_order.repair_order_ids), 0)
        sale_order.action_confirm()
        # Quantity set on the "create repair" product doesn't affect the number of RO created
        self.assertEqual(len(sale_order.repair_order_ids), 1)
        repair_order = sale_order.repair_order_ids[0]
        self.assertEqual(sale_order, repair_order.sale_order_id)
        self.assertEqual(repair_order.state, 'confirmed')
        order_line.product_uom_qty = 0
        self.assertEqual(repair_order.state, 'cancel')
        order_line.product_uom_qty = 1
        line_section.name = 'updated section'
        self.assertEqual(repair_order.state, 'confirmed')
        repair_order.action_repair_cancel()
        self.assertTrue(float_is_zero(order_line.product_uom_qty, 2))
        order_line.product_uom_qty = 3
        self.assertEqual(repair_order.state, 'confirmed')
        # Add RO line
        ro_form = Form(repair_order)
        with ro_form.move_ids.new() as ro_line_form:
            ro_line_form.repair_line_type = 'add'
            ro_line_form.product_id = self.product_product_11
            ro_line_form.product_uom_qty = 1
        ro_form.save()
        ro_line_0 = repair_order.move_ids[0]
        sol_part_0 = ro_line_0.sale_line_id
        self.assertEqual(float_compare(sol_part_0.product_uom_qty, ro_line_0.product_uom_qty, 2), 0)
        # chg qty in SO -> No effect on RO
        sol_part_0.product_uom_qty = 5
        self.assertNotEqual(float_compare(sol_part_0.product_uom_qty, ro_line_0.product_uom_qty, 2), 0)
        # chg qty in RO -> Update qty in SO
        ro_line_0.product_uom_qty = 3
        self.assertEqual(float_compare(sol_part_0.product_uom_qty, ro_line_0.product_uom_qty, 2), 0)
        # with/without warranty
        self.assertFalse(float_is_zero(sol_part_0.price_unit, 2))
        repair_order.under_warranty = True
        self.assertTrue(float_is_zero(sol_part_0.price_unit, 2))
        repair_order.under_warranty = False
        self.assertFalse(float_is_zero(sol_part_0.price_unit, 2))

        # stock_move transitions
        #   add -> remove -> add -> recycle -> add transitions
        ro_line_0.repair_line_type = 'remove'
        self.assertTrue(float_is_zero(sol_part_0.product_uom_qty, 2))
        ro_line_0.repair_line_type = 'add'
        self.assertEqual(float_compare(sol_part_0.product_uom_qty, ro_line_0.product_uom_qty, 2), 0)
        ro_line_0.repair_line_type = 'recycle'
        self.assertTrue(float_is_zero(sol_part_0.product_uom_qty, 2))
        ro_line_0.repair_line_type = 'add'
        self.assertEqual(float_compare(sol_part_0.product_uom_qty, ro_line_0.product_uom_qty, 2), 0)
        #   remove and recycle line : not added to SO.
        sol_count = len(sale_order.order_line)
        with ro_form.move_ids.new() as ro_line_form:
            ro_line_form.repair_line_type = 'remove'
            ro_line_form.product_id = self.product_product_12
            ro_line_form.product_uom_qty = 1
        with ro_form.move_ids.new() as ro_line_form:
            ro_line_form.repair_line_type = 'recycle'
            ro_line_form.product_id = self.product_product_13
            ro_line_form.product_uom_qty = 1
        ro_form.save()
        ro_line_1 = repair_order.move_ids[1]
        self.assertEqual(len(sale_order.order_line), sol_count)
        # remove to add -> added to SO
        ro_line_1.repair_line_type = 'add'
        sol_part_1 = ro_line_1.sale_line_id
        self.assertNotEqual(len(sale_order.order_line), sol_count)
        self.assertEqual(float_compare(sol_part_1.product_uom_qty, ro_line_1.product_uom_qty, 2), 0)
        # delete 'remove to add' line in RO -> SOL qty set to 0
        repair_order.move_ids = [(2, ro_line_1.id, 0)]
        self.assertTrue(float_is_zero(sol_part_1.product_uom_qty, 2))

        # repair_order.action_repair_end()
        #   -> order_line.qty_delivered == order_line.product_uom_qty
        #   -> "RO Lines"'s SOL.qty_delivered == move.quantity
        for line in repair_order.move_ids:
            line.quantity = line.product_uom_qty
        repair_order.action_repair_end()
        self.assertEqual(order_line.product_uom_qty, order_line.qty_delivered)
        self.assertEqual(float_compare(sol_part_0.product_uom_qty, ro_line_0.quantity, 2), 0)
        self.assertTrue(float_is_zero(sol_part_1.qty_delivered, 2))

    def test_purchase_price_so_create_from_repair(self):
        """
        Test that the purchase price is correctly set on the SO line,
        when creating a SO from a repair order.
        """
        if not self.env['ir.module.module'].search([('name', '=', 'sale_margin'), ('state', '=', 'installed')]):
            self.skipTest("sale_margin is not installed, so there is no purchase price to test")
        self.product_product_11.standard_price = 10
        repair = self.env['repair.order'].create({
            'partner_id': self.res_partner_1.id,
            'product_id': self.product_product_3.id,
            'picking_type_id': self.stock_warehouse.repair_type_id.id,
            'move_ids': [
                (0, 0, {
                    'repair_line_type': 'add',
                    'product_id': self.product_product_11.id,
                })
            ],
        })
        repair.action_create_sale_order()
        self.assertEqual(repair.sale_order_id.order_line.product_id, self.product_product_11)
        self.assertEqual(repair.sale_order_id.order_line.purchase_price, 10)

    def test_repair_components_lots_show_in_invoice(self):
        """
        Test that the lots of the components of a repair order are shown in the invoice.
        Also checks that picking description is propogated to sales orders and invoices.
        """
        quant = self.create_quant(self.product_storable_serial, 1)
        quant.action_apply_inventory()
        repair_order = self.env['repair.order'].create({
            'product_id': self.product_product_3.id,
            'uom_id': self.product_product_3.uom_id.id,
            'partner_id': self.res_partner_12.id,
            'move_ids': [
                Command.create({
                    'product_id': self.product_storable_serial.id,
                    'product_uom_qty': 1.0,
                    'state': 'draft',
                    'repair_line_type': 'add',
                    'description_picking': 'Picking Description',
                })
            ],
        })
        repair_order.action_validate()
        repair_order.action_repair_end()
        repair_order.action_create_sale_order()
        sale_order = repair_order.sale_order_id
        sale_order.action_confirm()
        invoice = sale_order._create_invoices()
        invoice.action_post()
        res = invoice._get_invoiced_lot_values()
        self.assertEqual(len(res), 1, "The invoice should have one line")
        self.assertEqual(res[0]['product_name'], self.product_storable_serial.display_name, "The product name should be the same")
        self.assertEqual(res[0]['lot_name'], quant.lot_id.name, "The lot name should be the same")
        self.assertEqual(sale_order.order_line[0].name, 'Picking Description')
        self.assertEqual(invoice.line_ids[0].name, 'Picking Description')

    def test_delivered_qty_of_generated_so(self):
        """
        Test that checks that `qty_delivered` of the generated SOL is correctly set when the repair is done.
        """
        repair_order = self._create_repair_order_with_moves_and_services()
        repair_order.action_validate()
        repair_order.action_repair_end()
        self.assertEqual(repair_order.state, 'done')
        self.assertEqual(repair_order.move_ids.quantity, 1.0)
        repair_order.action_create_sale_order()
        sale_order = repair_order.sale_order_id
        sale_order.action_confirm()
        self.assertEqual(sale_order.order_line.mapped('qty_delivered'), [1.0, 2.0])

    def test_sale_order_line_discount_on_repair_order(self):
        """
        Test that the discount on the sale order line created from a repair order is correctly set.
        """
        repair_order = self.repair0
        repair_order.action_create_sale_order()
        sale_line = repair_order.move_ids.sale_line_id
        sale_line.discount = 15
        repair_order.action_validate()
        repair_order.action_repair_end()
        self.assertEqual(sale_line.discount, 15)

    def test_invoice_discount_on_repair_order(self):
        """
        Test that the discount on the invoice line created from a repair order is correctly set and avoid breaking if
        discount on account.move.line is changed into a computed field.
        """
        repair_order = self.repair0
        repair_order.action_create_invoice()
        invoice_line_ids = repair_order.move_ids.invoice_line_ids
        invoice_line_ids.discount = 15
        repair_order.action_validate()
        repair_order.action_repair_end()
        self.assertEqual(invoice_line_ids.discount, 15)

    def test_repair_invoice_binding(self):
        """
        Test that the repair order is correctly linked to the invoice created directly from it.
        """
        repair_order = self._create_simple_repair_order()
        self._create_simple_part_move(repair_order.id, 2.0, product=self.product_product_11)
        self.env['stock.move'].create({
            'repair_line_type': 'remove',
            'product_id': self.product_product_12.id,
            'product_uom_qty': 1.0,
            'repair_id': repair_order.id,
        })
        self.env['stock.move'].create({
            'repair_line_type': 'recycle',
            'product_id': self.product_product_13.id,
            'product_uom_qty': 1.0,
            'repair_id': repair_order.id,
        })
        repair_order.action_validate()
        repair_order.action_repair_end()
        repair_order.action_create_invoice()
        invoice = repair_order.invoice_ids
        self.assertEqual(len(invoice), 1)
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.assertEqual(invoice.move_type, 'out_invoice')
        repair_order.under_warranty = True
        self.assertEqual(invoice.invoice_line_ids[0].price_unit, 0)
        repair_order.under_warranty = False
        self.assertEqual(invoice.invoice_line_ids[0].price_unit, 30.0)
        invoice.action_post()  # After posting, toggling "Under Warranty" should not impact the invoice lines
        repair_order.under_warranty = True
        self.assertEqual(invoice.invoice_line_ids[0].price_unit, 30.0)

    def test_invoice_fields_propagation(self):
        repair_order = self._create_repair_order_with_moves_and_services()
        repair_order.action_create_invoice()
        invoice = repair_order.invoice_ids
        inv_part_line = invoice.invoice_line_ids.filtered(lambda l: l.product_id == self.product_product_11)
        inv_service_line = invoice.invoice_line_ids.filtered(lambda l: l.product_id == self.product_order_repair)
        price_part = inv_part_line.price_unit
        price_service = inv_service_line.price_unit

        # Initial propagation
        self.assertEqual(inv_part_line.quantity, 1)
        self.assertEqual(inv_part_line.product_uom_id, self.uom_unit)

        self.assertEqual(inv_service_line.quantity, 2)
        self.assertEqual(inv_service_line.product_uom_id, self.uom_unit)

        # Propagation after invoice creation
        repair_order.move_ids[0].write({
            'product_uom_qty': 5,
            'uom_id': self.uom_dozen.id,
        })
        repair_order.repair_service_line_ids[0].write({
            'quantity': 6,
            'uom_id': self.uom_dozen.id,
        })
        self.assertEqual(inv_part_line.quantity, 5)
        self.assertEqual(inv_part_line.product_uom_id, self.uom_dozen)
        self.assertEqual(inv_part_line.price_unit, price_part * self.uom_dozen.factor)

        self.assertEqual(inv_service_line.quantity, 6)
        self.assertEqual(inv_service_line.product_uom_id, self.uom_dozen)
        self.assertEqual(inv_service_line.price_unit, price_service * self.uom_dozen.factor)

        repair_order.move_ids[0].unlink()
        repair_order.repair_service_line_ids[0].unlink()

        self.assertEqual(inv_part_line.quantity, 0)
        self.assertEqual(inv_service_line.quantity, 0)

    def test_sale_order_fields_propagation(self):
        repair_order = self._create_repair_order_with_moves_and_services()
        repair_order.action_create_sale_order()
        sale_order = repair_order.sale_order_id
        so_part_line = sale_order.order_line.filtered(lambda l: l.product_id == self.product_product_11)
        so_service_line = sale_order.order_line.filtered(lambda l: l.product_id == self.product_order_repair)

        # Initial Propagation
        self.assertEqual(so_part_line.product_uom_qty, 1)
        self.assertEqual(so_part_line.product_uom_id, self.uom_unit)

        self.assertEqual(so_service_line.product_uom_qty, 2)
        self.assertEqual(so_service_line.product_uom_id, self.uom_unit)

        # Propagation after sale order creation
        repair_order.move_ids[0].write({
            'product_uom_qty': 10.0,
            'quantity': 10,
            'uom_id': self.uom_dozen.id,
        })
        repair_order.repair_service_line_ids[0].write({
            'quantity': 12.0,
            'uom_id': self.uom_dozen.id,
        })

        self.assertEqual(so_part_line.product_uom_qty, 10)
        self.assertEqual(so_part_line.product_uom_id, self.uom_dozen)

        self.assertEqual(so_service_line.product_uom_qty, 12)
        self.assertEqual(so_service_line.product_uom_id, self.uom_dozen)

        repair_order.move_ids[0].unlink()
        repair_order.repair_service_line_ids[0].unlink()

        self.assertEqual(so_part_line.product_uom_qty, 0)
        self.assertEqual(so_service_line.product_uom_qty, 0)

    def test_warranty_sets_repair_service_sale_order_line_price_to_zero(self):
        repair_order = self._create_repair_order_with_moves_and_services()
        repair_order.action_create_sale_order()
        repair_order.under_warranty = True

        repair_order.action_validate()
        repair_order.action_repair_end()

        self.assertEqual(repair_order.repair_service_line_ids.sale_line_id.price_unit, 0.0)
