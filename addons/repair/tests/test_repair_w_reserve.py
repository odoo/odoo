# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.fields import Datetime
from odoo.tests import tagged
from datetime import timedelta
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestRepairWithReserve(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestRepairWithReserve, cls).setUpClass()
        # Partners
        cls.res_partner_1 = cls.env['res.partner'].create({'name': 'Wood Corner'})
        cls.res_partner_address_1 = cls.env['res.partner'].create({'name': 'Willie Burke', 'parent_id': cls.res_partner_1.id})
        cls.res_partner_12 = cls.env['res.partner'].create({'name': 'Partner 12'})

        # Locations
        cls.stock_warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.stock_location_14 = cls.env['stock.location'].create({
            'name': 'Shelf 2',
            'location_id': cls.stock_warehouse.lot_stock_id.id,
        })
        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')

        # Products
        cls.repair_product = cls.env['product.product'].create({
            'name': "Repair Product",
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })

        cls.avail_product = cls.env['product.product'].create({
            'name': "Available Product",
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.partial_product = cls.env['product.product'].create({
            'name': "Parital_Available Product",
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.not_avail_product = cls.env['product.product'].create({
            'name': "Not Available Product",
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })

        cls.picking = cls.env.ref('stock.picking_type_in')

    def _create_product(self, tracking='none', name=False):
        return self.env['product.product'].create({
            'name': name or f'Product {tracking}',
            'type': 'product',
            'tracking': tracking,
            'categ_id': self.env.ref('product.product_category_all').id,
        })

    def _create_repair_order_with_product(self, product_to_repair):
        partner = self.res_partner_address_1
        return self.env['repair.order'].create({
            'product_id': product_to_repair.id,
            'product_uom': product_to_repair.uom_id.id,
            'address_id': partner.id,
            'guarantee_limit': '2019-01-01',
            'invoice_method': 'none',
            'partner_invoice_id': partner.id,
            'location_id': self.stock_warehouse.lot_stock_id.id,
            'partner_id': self.res_partner_12.id
        })

    def _create_operation(self, product_to_add, repair_id=False, qty=0.0, price_unit=0.0):
        return self.env['repair.line'].create({
            'name': 'Add The product',
            'type': 'add',
            'product_id': product_to_add.id,
            'product_uom_qty': qty,
            'product_uom': product_to_add.uom_id.id,
            'price_unit': price_unit,
            'repair_id': repair_id,
            'location_id': self.stock_warehouse.lot_stock_id.id,
            'location_dest_id': product_to_add.property_stock_production.id,
            'company_id': self.env.company.id,
        })

    def test_repair_reserve_flow(self):
        '''This test create a flow of repair using 3 Parts:
        a fully-stocked product, a partially-stocked product,
        and a zero-stock product. We will later refill the stock
        and complete the flow'''

        repair = self._create_repair_order_with_product(self.repair_product)

        op1 = self._create_operation(
            self.avail_product,
            repair_id=repair.id,
            qty=2.0,
            price_unit=25.0)
        op2 = self._create_operation(
            self.partial_product,
            repair_id=repair.id,
            qty=10.0,
            price_unit=25.0)
        op3 = self._create_operation(
            self.not_avail_product,
            repair_id=repair.id,
            qty=3.0,
            price_unit=25.0)

        self.assertEqual(repair.state, 'draft')

        # Assign stock quantities
        quants = self.env['stock.quant'].create({
            'location_id': self.stock_location_14.id,
            'product_id': self.avail_product.id,
            'inventory_quantity': 5
        })

        quants |= self.env['stock.quant'].create({
            'location_id': self.stock_location_14.id,
            'product_id': self.partial_product.id,
            'inventory_quantity': 5
        })

        quants |= self.env['stock.quant'].create({
            'location_id': self.stock_location_14.id,
            'product_id': self.not_avail_product.id,
            'inventory_quantity': 0
        })
        quants.action_apply_inventory()

        self.assertEqual(op1.state, 'draft')
        self.assertEqual(op2.state, 'draft')
        self.assertEqual(op3.state, 'draft')

        repair.action_repair_confirm()

        self.assertEqual(op1.state, 'confirmed')
        self.assertEqual(op2.state, 'confirmed')
        self.assertEqual(op3.state, 'confirmed')

        self.assertEqual(op1.move_id.state, 'assigned')
        self.assertEqual(op2.move_id.state, 'partially_available')
        self.assertEqual(op3.move_id.state, 'confirmed')

        # Updating stock for the partially available product
        self.assertEqual(repair.operations_availability_state, 'late')
        self.assertEqual(op2.forecast_availability, 5.0)

        self.env['stock.quant']._update_available_quantity(
            self.partial_product,
            self.stock_location_14,
            10.0
        )
        op2.move_id._compute_forecast_information()

        self.assertEqual(op2.forecast_availability, 10.0)
        self.assertEqual(repair.operations_availability_state, 'late')

        # Create a move to re-stock the unavailable product
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location_14.id,
            'product_id': self.not_avail_product.id,
            'product_uom': self.not_avail_product.uom_id.id,
            'product_uom_qty': 10.0,
            'date': Datetime.now() + timedelta(days=3),
            'picking_type_id': self.picking.id,
        })
        move1._action_confirm()
        move1._compute_forecast_information()
        op3.move_id._compute_forecast_information()
        repair._compute_operations_availability()

        self.assertEqual(op3.forecast_availability, 3)

        # The state is still late since the date of the repair order is now()
        self.assertEqual(repair.operations_availability_state, 'late')

        # Set the schedule date of the repair order > than the expected date of the parts
        repair.write({'schedule_date': Datetime.now() + timedelta(days=10)})
        self.assertEqual(repair.operations_availability_state, 'expected')

        # Finish the move
        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.reserved_qty, 10.0)
        self.assertEqual(move_line.qty_done, 0.0)
        move_line.qty_done = 10.0
        move1._action_done()
        self.assertEqual(move1.state, 'done')

        # Check the reservations
        self.assertEqual(op1.reserved_availability, 2.0)
        self.assertEqual(op2.reserved_availability, 5.0)
        self.assertEqual(op3.reserved_availability, 0.0)

        # Check availability button
        repair.action_assign()
        self.assertEqual(op1.reserved_availability, 2.0)
        self.assertEqual(op2.reserved_availability, 10.0)
        self.assertEqual(op3.reserved_availability, 3.0)

        # I check the state is in "Confirmed".
        self.assertEqual(repair.state, "confirmed")
        repair.action_repair_start()

        # I check the state is in "Under Repair".
        self.assertEqual(repair.state, "under_repair")

        # Repairing process for product is in Done state and I end Repair process by clicking on "End Repair" button.
        repair.action_repair_end()
        self.assertEqual(repair.state, "done")

        # Check if there is move lines
        self.assertEqual(len(repair.move_id.move_line_ids[0].consume_line_ids), 3)
        self.assertEqual(len(repair.move_id.move_line_ids[0]), 1)

        # Check if the move lines contain the parts
        self.assertEqual(repair.move_id.move_line_ids[0].product_id.name, self.repair_product.name)
        self.assertTrue(self.avail_product.name in repair.move_id.move_line_ids[0].consume_line_ids.product_id.mapped('name'))
        self.assertTrue(self.partial_product.name in repair.move_id.move_line_ids[0].consume_line_ids.product_id.mapped('name'))
        self.assertTrue(self.not_avail_product.name in repair.move_id.move_line_ids[0].consume_line_ids.product_id.mapped('name'))

        # Check if the quantities of the move lines equal the ops product qty
        self.assertEqual(repair.move_id.move_line_ids[0].qty_done, 1.0)
        self.assertEqual(
            repair.move_id.move_line_ids[0].consume_line_ids
                .filtered(lambda line: line.product_id.name == self.avail_product.name)[0].qty_done, 2.0)
        self.assertEqual(
            repair.move_id.move_line_ids[0].consume_line_ids
                .filtered(lambda line: line.product_id.name == self.partial_product.name)[0].qty_done, 10.0)
        self.assertEqual(
            repair.move_id.move_line_ids[0].consume_line_ids
                .filtered(lambda line: line.product_id.name == self.not_avail_product.name)[0].qty_done, 3.0)


    def test_add_product_after_confirm(self):
        repair = self._create_repair_order_with_product(self.repair_product)

        op1 = self._create_operation(
            self.avail_product,
            repair_id=repair.id,
            qty=5.0,
            price_unit=25.0)
        op2 = self._create_operation(
            self.partial_product,
            repair_id=repair.id,
            qty=6.0,
            price_unit=25.0)

        self.assertEqual(repair.state, 'draft')

        # Assign stock quantities
        quants = self.env['stock.quant'].create({
            'location_id': self.stock_location_14.id,
            'product_id': self.avail_product.id,
            'inventory_quantity': 5
        })

        quants |= self.env['stock.quant'].create({
            'location_id': self.stock_location_14.id,
            'product_id': self.partial_product.id,
            'inventory_quantity': 6
        })

        quants |= self.env['stock.quant'].create({
            'location_id': self.stock_location_14.id,
            'product_id': self.not_avail_product.id,
            'inventory_quantity': 7
        })
        quants.action_apply_inventory()

        self.assertEqual(op1.state, 'draft')
        self.assertEqual(op2.state, 'draft')

        repair.action_repair_confirm()

        self.assertEqual(op1.state, 'confirmed')
        self.assertEqual(op2.state, 'confirmed')

        self.assertEqual(op1.move_id.state, 'assigned')
        self.assertEqual(op2.move_id.state, 'assigned')

        self.assertEqual(repair.operations_availability_state, 'available')

        op3 = self._create_operation(
            self.not_avail_product,
            repair_id=repair.id,
            qty=7.0,
            price_unit=25.0)
        self.assertEqual(op3.move_id.state, 'assigned')

        # I check the state is in "Confirmed".
        self.assertEqual(repair.state, "confirmed")
        repair.action_repair_start()

        # I check the state is in "Under Repair".
        self.assertEqual(repair.state, "under_repair")

        # Repairing process for product is in Done state and I end Repair process by clicking on "End Repair" button.
        repair.action_repair_end()
        self.assertEqual(repair.state, "done")

        # Check if there is move lines
        self.assertEqual(len(repair.move_id.move_line_ids[0].consume_line_ids), 3)
        self.assertEqual(len(repair.move_id.move_line_ids[0]), 1)

        # Check if the move lines contain the parts
        self.assertEqual(repair.move_id.move_line_ids[0].product_id.name, self.repair_product.name)
        self.assertTrue(self.avail_product.name in repair.move_id.move_line_ids[0].consume_line_ids.product_id.mapped('name'))
        self.assertTrue(self.partial_product.name in repair.move_id.move_line_ids[0].consume_line_ids.product_id.mapped('name'))
        self.assertTrue(self.not_avail_product.name in repair.move_id.move_line_ids[0].consume_line_ids.product_id.mapped('name'))

        # Check if the quantities of the move lines equal the ops product qty
        self.assertEqual(repair.move_id.move_line_ids[0].qty_done, 1.0)
        self.assertEqual(
            repair.move_id.move_line_ids[0].consume_line_ids
                .filtered(lambda line: line.product_id.name == self.avail_product.name)[0].qty_done, 5.0)
        self.assertEqual(
            repair.move_id.move_line_ids[0].consume_line_ids
                .filtered(lambda line: line.product_id.name == self.partial_product.name)[0].qty_done, 6.0)
        self.assertEqual(
            repair.move_id.move_line_ids[0].consume_line_ids
                .filtered(lambda line: line.product_id.name == self.not_avail_product.name)[0].qty_done, 7.0)


    def test_reserve_unreserve_flow(self):
        repair = self._create_repair_order_with_product(self.repair_product)

        op1 = self._create_operation(
            self.avail_product,
            repair_id=repair.id,
            qty=5.0,
            price_unit=25.0)
        op2 = self._create_operation(
            self.partial_product,
            repair_id=repair.id,
            qty=6.0,
            price_unit=25.0)
        op3 = self._create_operation(
            self.not_avail_product,
            repair_id=repair.id,
            qty=7.0,
            price_unit=25.0)

        self.assertEqual(repair.state, 'draft')

        # Assign stock quantities
        quants = self.env['stock.quant'].create({
            'location_id': self.stock_location_14.id,
            'product_id': self.avail_product.id,
            'inventory_quantity': 5
        })

        quants |= self.env['stock.quant'].create({
            'location_id': self.stock_location_14.id,
            'product_id': self.partial_product.id,
            'inventory_quantity': 6
        })

        quants |= self.env['stock.quant'].create({
            'location_id': self.stock_location_14.id,
            'product_id': self.not_avail_product.id,
            'inventory_quantity': 7
        })
        quants.action_apply_inventory()

        self.assertEqual(op1.state, 'draft')
        self.assertEqual(op2.state, 'draft')
        self.assertEqual(op3.state, 'draft')

        repair.action_repair_confirm()

        self.assertEqual(op1.state, 'confirmed')
        self.assertEqual(op2.state, 'confirmed')
        self.assertEqual(op3.state, 'confirmed')

        self.assertEqual(op1.move_id.state, 'assigned')
        self.assertEqual(op2.move_id.state, 'assigned')
        self.assertEqual(op3.move_id.state, 'assigned')

        self.assertEqual(repair.operations_availability_state, 'available')

        # Check the reservations
        self.assertEqual(op1.reserved_availability, 5.0)
        self.assertEqual(op2.reserved_availability, 6.0)
        self.assertEqual(op3.reserved_availability, 7.0)

        # Check unreserve button
        repair.do_unreserve()
        self.assertEqual(op1.reserved_availability, 0.0)
        self.assertEqual(op2.reserved_availability, 0.0)
        self.assertEqual(op3.reserved_availability, 0.0)

        # Check availability button
        repair.action_assign()
        self.assertEqual(op1.reserved_availability, 5.0)
        self.assertEqual(op2.reserved_availability, 6.0)
        self.assertEqual(op3.reserved_availability, 7.0)

        # I check the state is in "Confirmed".
        self.assertEqual(repair.state, "confirmed")
        repair.action_repair_start()

        # I check the state is in "Under Repair".
        self.assertEqual(repair.state, "under_repair")

        # Repairing process for product is in Done state and I end Repair process by clicking on "End Repair" button.
        repair.action_repair_end()
        self.assertEqual(repair.state, "done")

        # Check if there is move lines
        self.assertEqual(len(repair.move_id.move_line_ids[0].consume_line_ids), 3)
        self.assertEqual(len(repair.move_id.move_line_ids[0]), 1)

        # Check if the move lines contain the parts
        self.assertEqual(repair.move_id.move_line_ids[0].product_id.name, self.repair_product.name)
        self.assertTrue(self.avail_product.name in repair.move_id.move_line_ids[0].consume_line_ids.product_id.mapped('name'))
        self.assertTrue(self.partial_product.name in repair.move_id.move_line_ids[0].consume_line_ids.product_id.mapped('name'))
        self.assertTrue(self.not_avail_product.name in repair.move_id.move_line_ids[0].consume_line_ids.product_id.mapped('name'))

        # Check if the quantities of the move lines equal the ops product qty
        self.assertEqual(repair.move_id.move_line_ids[0].qty_done, 1.0)
        self.assertEqual(
            repair.move_id.move_line_ids[0].consume_line_ids
                .filtered(lambda line: line.product_id.name == self.avail_product.name)[0].qty_done, 5.0)
        self.assertEqual(
            repair.move_id.move_line_ids[0].consume_line_ids
                .filtered(lambda line: line.product_id.name == self.partial_product.name)[0].qty_done, 6.0)
        self.assertEqual(
            repair.move_id.move_line_ids[0].consume_line_ids
                .filtered(lambda line: line.product_id.name == self.not_avail_product.name)[0].qty_done, 7.0)
