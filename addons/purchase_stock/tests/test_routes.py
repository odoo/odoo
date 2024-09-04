from odoo import Command
from odoo.tests import Form, TransactionCase


class TestRoutes(TransactionCase):

    def test_allow_rule_creation_for_route_without_company(self):
        self.env['res.config.settings'].write({
            'group_stock_adv_location': True,
            'group_stock_multi_locations': True,
        })

        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)

        location_1 = self.env['stock.location'].create({
            'name': 'loc1',
            'location_id': warehouse.id
        })

        location_2 = self.env['stock.location'].create({
            'name': 'loc2',
            'location_id': warehouse.id
        })

        receipt_1 = self.env['stock.picking.type'].create({
            'name': 'Receipts from loc1',
            'sequence_code': 'IN1',
            'code': 'incoming',
            'warehouse_id': warehouse.id,
            'default_location_dest_id': location_1.id,
        })

        receipt_2 = self.env['stock.picking.type'].create({
            'name': 'Receipts from loc2',
            'sequence_code': 'IN2',
            'code': 'incoming',
            'warehouse_id': warehouse.id,
            'default_location_dest_id': location_2.id,
        })

        route = self.env['stock.route'].create({
            'name': 'Buy',
            'company_id': False
        })

        with Form(route) as r:
            with r.rule_ids.new() as line:
                line.name = 'first rule'
                line.action = 'buy'
                line.picking_type_id = receipt_1
            with r.rule_ids.new() as line:
                line.name = 'second rule'
                line.action = 'buy'
                line.picking_type_id = receipt_2

    def test_delete_buy_route(self):
        """
        The user should be able to write on a warehouse even if the buy route
        does not exist anymore
        """
        wh = self.env['stock.warehouse'].search([], limit=1)

        buy_routes = self.env['stock.route'].search([('name', 'ilike', 'buy')])
        self.assertTrue(buy_routes)

        buy_routes.unlink()

        wh.reception_steps = 'two_steps'
        self.assertEqual(wh.reception_steps, 'two_steps')

    def test_cross_dock_with_purchase(self):
        customer_loc, supplier_loc = self.env['stock.warehouse']._get_partner_locations()
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.write({'reception_steps': 'two_steps', 'delivery_steps': 'pick_ship'})

        partner = self.env['res.partner'].create({'name': 'Vendor'})
        product = self.env['product.product'].create({
            'name': 'Cross-Dockable',
            'is_storable': True,
            'route_ids': [Command.link(warehouse.crossdock_route_id.id)],
            'seller_ids': [Command.create({'partner_id': partner.id})],
        })

        # Create a procurement for an Out using that should use the cross-dock route
        group = self.env['procurement.group'].create({'name': 'Test-cross-dock'})
        self.env['procurement.group'].run([self.env['procurement.group'].Procurement(
            product, 5, self.env.ref('uom.product_uom_unit'), customer_loc,
            product.name, '/', self.env.company, {'warehouse_id': warehouse, 'group_id': group})
        ])

        # No move should be created, instead should have created a Purchase Order
        receipt_move = self.env['stock.move'].search([('group_id', '=', group.id)])
        self.assertFalse(receipt_move)
        purchase_order = self.env['purchase.order'].search([('group_id', '=', group.id)])
        self.assertEqual(purchase_order.partner_id, partner)
        purchase_order.button_confirm()

        receipt_move = purchase_order.picking_ids.move_ids
        self.assertRecordValues(receipt_move, [{
            'location_id': supplier_loc.id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
            'location_final_id': customer_loc.id,
            'picking_type_id': warehouse.in_type_id.id,
        }])

        # Validate the chain
        receipt_move.write({'picked': True})
        receipt_move._action_done()

        cross_dock_move = receipt_move.move_dest_ids
        self.assertRecordValues(cross_dock_move, [{
            'location_id': warehouse.wh_input_stock_loc_id.id,
            'location_dest_id': warehouse.wh_output_stock_loc_id.id,
            'location_final_id': customer_loc.id,
            'picking_type_id': warehouse.xdock_type_id.id,
        }])
        cross_dock_move.write({'picked': True})
        cross_dock_move._action_done()

        delivery_move = cross_dock_move.move_dest_ids
        self.assertRecordValues(delivery_move, [{
            'location_id': warehouse.wh_output_stock_loc_id.id,
            'location_dest_id': customer_loc.id,
            'location_final_id': customer_loc.id,
            'picking_type_id': warehouse.out_type_id.id,
        }])
        delivery_move.write({'picked': True})
        delivery_move._action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product, customer_loc), 5)
