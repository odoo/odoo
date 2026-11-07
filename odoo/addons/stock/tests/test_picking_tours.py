# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests import Form, HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestStockPickingTour(HttpCase):
    def setUp(self):
        self.receipt = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
        })

        return super().setUp()

    def _get_picking_url(self, picking_id):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_incoming")
        return '/web#action=%s&id=%s&model=stock.picking&view_type=form' % (action['id'], picking_id)

    def test_detailed_op_no_save_1(self):
        """validate a receipt with some move without any save except the last one"""
        product_lot = self.env['product.product'].create({
            'name': 'Product Lot',
            'type': 'product',
            'tracking': 'lot',
        })
        url = self._get_picking_url(self.receipt.id)

        self.start_tour(url, 'test_detailed_op_no_save_1', login='admin', timeout=60)
        self.assertEqual(self.receipt.state, 'done')
        self.assertEqual(self.receipt.move_ids.product_uom_qty, 0)
        self.assertEqual(self.receipt.move_ids.quantity, 4)
        lot = self.env['stock.lot'].search([
            ('name', '=', 'lot1'),
            ('product_id', '=', product_lot.id),
        ])
        self.assertEqual(len(lot), 1)
        self.assertEqual(lot.product_qty, 4)

    def test_generate_serial_1(self):
        """generate some serial numbers in the detailed operation modal"""
        product_serial = self.env['product.product'].create({
            'name': 'Product Serial',
            'type': 'product',
            'tracking': 'serial',
        })
        url = self._get_picking_url(self.receipt.id)

        self.start_tour(url, 'test_generate_serial_1', login='admin', timeout=60)
        self.assertEqual(self.receipt.state, 'done')
        self.assertEqual(self.receipt.move_ids.product_uom_qty, 0)
        self.assertEqual(self.receipt.move_ids.quantity, 5)
        self.assertEqual(len(self.receipt.move_ids.move_line_ids), 5)

        serial = self.env['stock.lot'].search([
            ('name', 'ilike', 'serial_n_%'),
            ('product_id', '=', product_serial.id),
        ])
        self.assertEqual(len(serial), 5)

    def test_add_new_line(self):
        product_one, _ = self.env["product.product"].create([
            {
                'name': 'Product one',
                'type': 'product',
                'tracking': 'serial',
            },
            {
                'name': 'Product two',
                'type': 'product',
                'tracking': 'serial',
            }
        ])

        self.receipt.write({
            "move_ids": [Command.create({
                "name": "test",
                "product_uom_qty": 1,
                "product_id": product_one.id,
                "location_id": self.receipt.location_id.id,
                "location_dest_id": self.receipt.location_dest_id.id,
            })]
        })

        self.receipt.action_confirm()
        self.receipt.move_ids.move_line_ids.lot_name = "one"

        url = self._get_picking_url(self.receipt.id)
        self.start_tour(url, 'test_add_new_line', login='admin', timeout=60)

        names = self.receipt.move_ids.move_line_ids.mapped('lot_name')
        self.assertEqual(names, ["two", "one"])

    def test_add_new_line_in_detailled_op(self):
        """
        Check that the unsaved quantity/location changes of the detailed operations impact dynamically
        the creation of new move lines (considering the real avaible quantity rather than DB data's).
        """
        warehouse = self.env.ref("stock.warehouse0")
        product_lot = self.env['product.product'].create({
            'name': 'Product Lot',
            'type': 'product',
            'tracking': 'lot',
        })
        lot_1, lot_2, lot_3 = self.env['stock.lot'].create([
            {'name': 'LOT001', 'product_id': product_lot.id, 'company_id': warehouse.company_id.id},
            {'name': 'LOT002', 'product_id': product_lot.id, 'company_id': warehouse.company_id.id},
            {'name': 'LOT003', 'product_id': product_lot.id, 'company_id': warehouse.company_id.id},
        ])
        self.env['stock.quant']._update_available_quantity(product_lot, warehouse.lot_stock_id, quantity=10, lot_id=lot_1)
        self.env['stock.quant']._update_available_quantity(product_lot, warehouse.lot_stock_id, quantity=15, lot_id=lot_2)
        self.env['stock.quant']._update_available_quantity(product_lot, warehouse.lot_stock_id, quantity=10, lot_id=lot_3)
        partner = self.env['res.partner'].create({'name': 'Bob'})
        delivery = self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': warehouse.out_type_id.id,
            'partner_id': partner.id,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'move_ids': [Command.create({
                'name': product_lot.name,
                'product_id': product_lot.id,
                'location_id': warehouse.lot_stock_id.id,
                'location_dest_id': self.ref('stock.stock_location_customers'),
                'product_uom_qty': 20,
            })]
        })
        delivery.action_confirm()
        self.assertRecordValues(delivery.move_line_ids, [
            {'lot_id': lot_1.id, 'quantity': 10.0},
            {'lot_id': lot_2.id, 'quantity': 10.0},
        ])
        url = self._get_picking_url(delivery.id)
        self.start_tour(url, 'test_add_new_line_in_detailled_op', login='admin', timeout=100)
        self.assertRecordValues(delivery.move_line_ids.sorted("quantity"), [
            {'quantity': 2.0, 'lot_id': lot_1.id},
            {'quantity': 3.0, 'lot_id': lot_1.id},
            {'quantity': 15.0, 'lot_id': lot_2.id},
        ])

    def test_edit_existing_line(self):
        self.uom_unit = self.env.ref('uom.product_uom_unit')
        product_one = self.env['product.product'].create({
            'name': 'Product one',
            'type': 'product',
            'tracking': 'serial',
        })

        self.receipt.write({
            "move_ids": [Command.create({
                "name": "test",
                "product_id": product_one.id,
                "location_id": self.receipt.location_id.id,
                "location_dest_id": self.receipt.location_dest_id.id,
                "product_uom_qty": 1,
            })]
        })

        self.receipt.action_confirm()
        self.receipt.move_ids.move_line_ids.lot_name = "one"

        url = self._get_picking_url(self.receipt.id)
        self.start_tour(url, 'test_edit_existing_line', login='admin', timeout=60)

        names = self.receipt.move_ids.move_line_ids.mapped('lot_name')
        self.assertEqual(names, ["one", "two"])

    def test_onchange_serial_lot_ids(self):
        """
        Checks that onchange behaves correctly with respect to multiple unlinks
        """
        product_serial = self.env['product.product'].create({
            'name': 'PSerial',
            'type': 'product',
            'tracking': 'serial',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        lots = self.env['stock.lot'].create([{
            'name': 'SN01',
            'product_id': product_serial.id,
            'company_id': self.env.company.id,
        }, {
            'name': 'SN02',
            'product_id': product_serial.id,
            'company_id': self.env.company.id,
        }, {
            'name': 'SN03',
            'product_id': product_serial.id,
            'company_id': self.env.company.id,
        }])

        stock_location = self.env.ref('stock.stock_location_stock')
        for lot in lots:
            self.env['stock.quant']._update_available_quantity(product_serial, stock_location, 1, lot_id=lot)

        picking = self.env['stock.picking'].create({
            'location_id': stock_location.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'picking_type_id': self.ref('stock.picking_type_out'),
            'move_ids': [Command.create({
                'name': product_serial.name,
                'product_id': product_serial.id,
                'product_uom_qty': 3,
                'product_uom': product_serial.uom_id.id,
                'location_id': stock_location.id,
                'location_dest_id': self.ref('stock.stock_location_customers'),
            })]
        })
        picking.action_confirm()

        with Form(picking) as form:
            with form.move_ids_without_package.edit(0) as move_form:
                move_form.quantity = 3.0
                move_form.lot_ids = lots

        url = self._get_picking_url(picking.id)
        self.start_tour(url, 'test_onchange_twice_lot_ids', login='admin', step_delay=100)
        self.assertRecordValues(picking.move_ids, [{"quantity": 1, "lot_ids": lots[2].ids}])
