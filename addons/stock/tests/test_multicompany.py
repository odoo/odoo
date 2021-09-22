# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, Form


class TestMultiCompany(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestMultiCompany, cls).setUpClass()
        group_user = cls.env.ref('base.group_user')
        group_stock_manager = cls.env.ref('stock.group_stock_manager')

        cls.company_a = cls.env['res.company'].create({'name': 'Company A'})
        cls.company_b = cls.env['res.company'].create({'name': 'Company B'})
        cls.warehouse_a = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_a.id)], limit=1)
        cls.warehouse_b = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_b.id)], limit=1)
        cls.stock_location_a = cls.warehouse_a.lot_stock_id
        cls.stock_location_b = cls.warehouse_b.lot_stock_id

        cls.user_a = cls.env['res.users'].create({
            'name': 'user company a with access to company b',
            'login': 'user a',
            'groups_id': [(6, 0, [group_user.id, group_stock_manager.id])],
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id, cls.company_b.id])]
        })
        cls.user_b = cls.env['res.users'].create({
            'name': 'user company b with access to company a',
            'login': 'user b',
            'groups_id': [(6, 0, [group_user.id, group_stock_manager.id])],
            'company_id': cls.company_b.id,
            'company_ids': [(6, 0, [cls.company_a.id, cls.company_b.id])]
        })

    def test_picking_type_1(self):
        """As a user of Company A, check it is not possible to use a warehouse of Company B in a
        picking type of Company A.
        """
        picking_type_company_a = self.env['stock.picking.type'].search([
            ('company_id', '=', self.company_a.id)
        ], limit=1)
        with self.assertRaises(UserError):
            picking_type_company_a.warehouse_id = self.warehouse_b

    def test_picking_type_2(self):
        """As a user of Company A, check it is not possible to change the company on an existing
        picking type of Company A to Company B.
        """
        picking_type_company_a = self.env['stock.picking.type'].search([
            ('company_id', '=', self.company_a.id)
        ], limit=1)
        with self.assertRaises(UserError):
            picking_type_company_a.with_user(self.user_a).company_id = self.company_b

    def test_putaway_1(self):
        """As a user of Company A, create a putaway rule with locations of Company A and set the
        company to Company B before saving. Check it is not possible.
        """
        stock_location_a_1 = self.env['stock.location'].with_user(self.user_a).create({
            'location_id': self.stock_location_a.id,
            'usage': 'internal',
            'name': 'A_1',
        })
        putaway_form = Form(self.env['stock.putaway.rule'])
        putaway_form.location_in_id = self.stock_location_a
        putaway_form.location_out_id = stock_location_a_1
        putaway_form.company_id = self.company_b
        with self.assertRaises(UserError):
            putaway_form.save()

    def test_putaway_2(self):
        """As a user of Company A, check it is not possible to change the company on an existing
        putaway rule to Company B.
        """
        stock_location_a_1 = self.env['stock.location'].with_user(self.user_a).create({
            'name': 'A_1',
            'location_id': self.stock_location_a.id,
            'usage': 'internal',
        })
        putaway_rule = self.env['stock.putaway.rule'].with_user(self.user_a).create({
            'location_in_id': self.stock_location_a.id,
            'location_out_id': stock_location_a_1.id
        })
        with self.assertRaises(UserError):
            putaway_rule.company_id = self.company_b

    def test_company_1(self):
        """Check it is not possible to use the internal transit location of Company B on Company A."""
        with self.assertRaises(UserError):
            self.company_a.internal_transit_location_id = self.company_b.internal_transit_location_id

    def test_partner_1(self):
        """On a partner without company, as a user of Company B, check it is not possible to use a
        location limited to Company A as `property_stock_supplier` or `property_stock_customer`.
        """
        shared_partner = self.env['res.partner'].create({
            'name': 'Shared Partner',
            'company_id': False,
        })
        with self.assertRaises(UserError):
            shared_partner.with_user(self.user_b).property_stock_customer = self.stock_location_a

    def test_inventory_1(self):
        """Create a quant (inventory adjustment) in Company A for a product limited to Company A and
        as a user of company B, apply the inventory adjustment and set its counted quantity to 10
        before validating. The quant and stock moves should belong to Company A.
        """
        product = self.env['product.product'].create({
            'type': 'product',
            'company_id': self.company_a.id,
            'name': 'Product limited to company A',
        })
        inventory_quant = self.env['stock.quant'].with_user(self.user_a).with_context(inventory_mode=True).create({
            'location_id': self.stock_location_a.id,
            'product_id': product.id,
            'inventory_quantity': 0
        })
        self.assertEqual(inventory_quant.company_id, self.company_a)
        inventory_quant.with_user(self.user_b).inventory_quantity = 10
        inventory_quant.with_user(self.user_b).action_apply_inventory()
        last_move_id = self.env['stock.move'].search([('is_inventory', '=', True)])[-1]
        self.assertEqual(inventory_quant.company_id, self.company_a)
        self.assertEqual(last_move_id.company_id, self.company_a)
        self.assertEqual(last_move_id.quantity_done, 10)
        self.assertEqual(last_move_id.location_id.company_id, self.company_a)

    def test_inventory_2(self):
        """Try to create a quant (inventory adjustment) in Company A and check it is not possible to use
        products limited to Company B in it.
        """
        product = self.env['product.product'].create({
            'name': 'product limited to company b',
            'company_id': self.company_b.id,
            'type': 'product'
        })

        with self.assertRaises(UserError):
            self.env['stock.quant'].with_user(self.user_a).with_context(inventory_mode=True).create({
                'location_id': self.stock_location_a.id,
                'product_id': product.id,
                'inventory_quantity': 10
        })

    def test_picking_1(self):
        """As a user of Company A, create a picking and use a picking type of Company B, check the
        create picking belongs to Company B.
        """
        picking_type_company_b = self.env['stock.picking.type'].search([('company_id', '=', self.company_b.id)], limit=1)
        picking_form = Form(self.env['stock.picking'].with_user(self.user_a))
        picking_form.picking_type_id = picking_type_company_b
        picking = picking_form.save()
        self.assertEqual(picking.company_id, self.company_b)

    def test_location_1(self):
        """Check it is not possible to set a location of Company B under a location of Company A."""
        with self.assertRaises(UserError):
            self.stock_location_b.location_id = self.stock_location_a

    def test_lot_1(self):
        """Check it is possible to create a stock.production.lot with the same name in Company A and
        Company B"""
        product_lot = self.env['product.product'].create({
            'type': 'product',
            'tracking': 'lot',
            'name': 'product lot',
        })
        self.env['stock.production.lot'].create({
            'name': 'lotA',
            'company_id': self.company_a.id,
            'product_id': product_lot.id,
        })
        self.env['stock.production.lot'].create({
            'name': 'lotA',
            'company_id': self.company_b.id,
            'product_id': product_lot.id,
        })

    def test_lot_2(self):
        """Validate a picking of Company A receiving lot1 while being logged into Company B. Check
        the lot is created in Company A.
        """
        product = self.env['product.product'].create({
            'type': 'product',
            'tracking': 'serial',
            'name': 'product',
        })
        picking = self.env['stock.picking'].with_user(self.user_a).create({
            'picking_type_id': self.warehouse_a.in_type_id.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.stock_location_a.id,
        })
        self.assertEqual(picking.company_id, self.company_a)
        move1 = self.env['stock.move'].create({
            'name': 'test_lot_2',
            'picking_type_id': picking.picking_type_id.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 1.0,
            'picking_id': picking.id,
            'company_id': picking.company_id.id,
        })
        picking.with_user(self.user_b).action_confirm()
        self.assertEqual(picking.state, 'assigned')
        move1.with_user(self.user_b).move_line_ids[0].qty_done = 1
        move1.with_user(self.user_b).move_line_ids[0].lot_name = 'receipt_serial'
        self.assertEqual(move1.move_line_ids[0].company_id, self.company_a)
        picking.with_user(self.user_b).button_validate()
        self.assertEqual(picking.state, 'done')
        created_serial = self.env['stock.production.lot'].search([
            ('name', '=', 'receipt_serial')
        ])
        self.assertEqual(created_serial.company_id, self.company_a)

    def test_orderpoint_1(self):
        """As a user of company A, create an orderpoint for company B. Check itsn't possible to
        use a warehouse of companny A"""
        product = self.env['product.product'].create({
            'type': 'product',
            'name': 'shared product',
        })
        orderpoint = Form(self.env['stock.warehouse.orderpoint'].with_user(self.user_a))
        orderpoint.company_id = self.company_b
        orderpoint.warehouse_id = self.warehouse_b
        orderpoint.location_id = self.stock_location_a
        orderpoint.product_id = product
        with self.assertRaises(UserError):
            orderpoint.save()
        orderpoint.location_id = self.stock_location_b
        orderpoint = orderpoint.save()
        self.assertEqual(orderpoint.company_id, self.company_b)

    def test_orderpoint_2(self):
        """As a user of Company A, check it is not possible to change the company on an existing
        orderpoint to Company B.
        """
        product = self.env['product.product'].create({
            'type': 'product',
            'name': 'shared product',
        })
        orderpoint = Form(self.env['stock.warehouse.orderpoint'].with_user(self.user_a))
        orderpoint.company_id = self.company_a
        orderpoint.warehouse_id = self.warehouse_a
        orderpoint.location_id = self.stock_location_a
        orderpoint.product_id = product
        orderpoint = orderpoint.save()
        self.assertEqual(orderpoint.company_id, self.company_a)
        with self.assertRaises(UserError):
            orderpoint.company_id = self.company_b.id

    def test_product_1(self):
        """ As an user of Company A, checks we can or cannot create new product
        depending of its `company_id`."""
        # Creates a new product with no company_id and set a responsible.
        # The product must be created as there is no company on the product.
        product_form = Form(self.env['product.template'].with_user(self.user_a))
        product_form.name = 'Paramite Pie'
        product_form.responsible_id = self.user_b
        product = product_form.save()

        self.assertEqual(product.company_id.id, False)
        self.assertEqual(product.responsible_id.id, self.user_b.id)

        # Creates a new product belong to Company A and set a responsible belong
        # to Company B. The product mustn't be created as the product and the
        # user don't belong of the same company.
        self.user_b.company_ids = [(6, 0, [self.company_b.id])]
        product_form = Form(self.env['product.template'].with_user(self.user_a))
        product_form.name = 'Meech Munchy'
        product_form.company_id = self.company_a
        product_form.responsible_id = self.user_b

        with self.assertRaises(UserError):
            # Raises an UserError for company incompatibility.
            product = product_form.save()

        # Creates a new product belong to Company A and set a responsible belong
        # to Company A & B (default B). The product must be created as the user
        # belongs to product's company.
        self.user_b.company_ids = [(6, 0, [self.company_a.id, self.company_b.id])]
        product_form = Form(self.env['product.template'].with_user(self.user_a))
        product_form.name = 'Scrab Cake'
        product_form.company_id = self.company_a
        product_form.responsible_id = self.user_b
        product = product_form.save()

        self.assertEqual(product.company_id.id, self.company_a.id)
        self.assertEqual(product.responsible_id.id, self.user_b.id)

    def test_warehouse_1(self):
        """As a user of Company A, on its main warehouse, see it is impossible to change the
        company_id, to use a view location of another company, to set a picking type to one
        of another company
        """
        with self.assertRaises(UserError):
            self.warehouse_a.company_id = self.company_b.id
        with self.assertRaises(UserError):
            self.warehouse_a.view_location_id = self.warehouse_b.view_location_id
        with self.assertRaises(UserError):
            self.warehouse_a.pick_type_id = self.warehouse_b.pick_type_id

    def test_move_1(self):
        """See it is not possible to confirm a stock move of Company A with a picking type of
        Company B.
        """
        product = self.env['product.product'].create({
            'name': 'p1',
            'type': 'product'
        })
        picking_type_b = self.env['stock.picking.type'].search([
            ('company_id', '=', self.company_b.id),
        ], limit=1)
        move = self.env['stock.move'].create({
            'company_id': self.company_a.id,
            'picking_type_id': picking_type_b.id,
            'location_id': self.stock_location_a.id,
            'location_dest_id': self.stock_location_a.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'name': 'stock_move',
        })
        with self.assertRaises(UserError):
            move._action_confirm()

    def test_move_2(self):
        """See it is not possible to confirm a stock move of Company A with a destination location
        of Company B.
        """
        product = self.env['product.product'].create({
            'name': 'p1',
            'type': 'product'
        })
        picking_type_b = self.env['stock.picking.type'].search([
            ('company_id', '=', self.company_b.id),
        ], limit=1)
        move = self.env['stock.move'].create({
            'company_id': self.company_a.id,
            'picking_type_id': picking_type_b.id,
            'location_id': self.stock_location_a.id,
            'location_dest_id': self.stock_location_b.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'name': 'stock_move',
        })
        with self.assertRaises(UserError):
            move._action_confirm()

    def test_move_3(self):
        """See it is not possible to confirm a stock move of Company A with a product restricted to
        Company B.
        """
        product = self.env['product.product'].create({
            'name': 'p1',
            'type': 'product',
            'company_id': self.company_b.id,
        })
        picking_type_b = self.env['stock.picking.type'].search([
            ('company_id', '=', self.company_b.id),
        ], limit=1)
        move = self.env['stock.move'].create({
            'company_id': self.company_a.id,
            'picking_type_id': picking_type_b.id,
            'location_id': self.stock_location_a.id,
            'location_dest_id': self.stock_location_a.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'name': 'stock_move',
        })
        with self.assertRaises(UserError):
            move._action_confirm()

    def test_intercom_lot_push(self):
        """ Create a push rule to transfer products received in inter company
        transit location to company b. Move a lot product from company a to the
        transit location. Check the move created by the push rule is not chained
        with previous move, and no product are reserved from inter-company
        transit. """
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        intercom_location = self.env.ref('stock.stock_location_inter_wh')
        intercom_location.write({'active': True})

        product_lot = self.env['product.product'].create({
            'type': 'product',
            'tracking': 'lot',
            'name': 'product lot',
        })

        picking_type_to_transit = self.env['stock.picking.type'].create({
            'name': 'To Transit',
            'sequence_code': 'TRANSIT',
            'code': 'outgoing',
            'company_id': self.company_a.id,
            'warehouse_id': False,
            'default_location_src_id': self.stock_location_a.id,
            'default_location_dest_id': intercom_location.id,
            'sequence_id': self.env['ir.sequence'].create({
                'code': 'transit',
                'name': 'transit sequence',
                'company_id': self.company_a.id,
            }).id,
        })

        route = self.env['stock.location.route'].create({
            'name': 'Push',
            'company_id': False,
            'rule_ids': [(0, False, {
                'name': 'create a move to company b',
                'company_id': self.company_b.id,
                'location_src_id': intercom_location.id,
                'location_id': self.stock_location_b.id,
                'action': 'push',
                'auto': 'manual',
                'picking_type_id': self.warehouse_b.in_type_id.id,
            })],
        })

        move_from_supplier = self.env['stock.move'].create({
            'company_id': self.company_a.id,
            'name': 'test_from_supplier',
            'location_id': supplier_location.id,
            'location_dest_id': self.stock_location_a.id,
            'product_id': product_lot.id,
            'product_uom': product_lot.uom_id.id,
            'product_uom_qty': 1.0,
            'picking_type_id': self.warehouse_a.in_type_id.id,
        })
        move_from_supplier._action_confirm()
        move_line_1 = move_from_supplier.move_line_ids[0]
        move_line_1.lot_name = 'lot 1'
        move_line_1.qty_done = 1.0
        move_from_supplier._action_done()
        lot_1 = move_line_1.lot_id

        move_to_transit = self.env['stock.move'].create({
            'company_id': self.company_a.id,
            'name': 'test_to_transit',
            'location_id': self.stock_location_a.id,
            'location_dest_id': intercom_location.id,
            'product_id': product_lot.id,
            'product_uom': product_lot.uom_id.id,
            'product_uom_qty': 1.0,
            'picking_type_id': picking_type_to_transit.id,
            'route_ids': [(4, route.id)],
        })
        move_to_transit._action_confirm()
        move_to_transit._action_assign()
        move_line_2 = move_to_transit.move_line_ids[0]
        self.assertTrue(move_line_2.lot_id, move_line_1.lot_id)
        move_line_2.qty_done = 1.0
        move_to_transit._action_done()

        move_push = self.env['stock.move'].search([('location_id', '=', intercom_location.id),
                                                   ('product_id', '=', product_lot.id)])
        self.assertTrue(move_push, 'No move created from push rules')
        self.assertEqual(move_push.state, "assigned")
        self.assertTrue(move_push.move_line_ids, "No move line created for the move")
        self.assertFalse(move_push in move_to_transit.move_dest_ids,
                         "Chained move created in transit location")
        self.assertNotEqual(move_push.move_line_ids.lot_id, move_line_2.lot_id,
                            "Reserved from transit location")
        picking_receipt = move_push.picking_id
        with self.assertRaises(UserError):
            picking_receipt.button_validate()

        move_line_3 = move_push.move_line_ids[0]
        move_line_3.lot_name = 'lot 2'
        move_line_3.qty_done = 1.0
        picking_receipt.button_validate()
        lot_2 = move_line_3.lot_id
        self.assertEqual(lot_1.company_id, self.company_a)
        self.assertEqual(lot_1.name, 'lot 1')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product_lot, intercom_location, lot_1), 1.0)
        self.assertEqual(lot_2.company_id, self.company_b)
        self.assertEqual(lot_2.name, 'lot 2')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product_lot, self.stock_location_b, lot_2), 1.0)

    def test_intercom_lot_pull(self):
        """Use warehouse of comany a to resupply warehouse of company b. Check
        pull rule works correctly in two companies and moves are unchained from
        inter-company transit location."""
        customer_location = self.env.ref('stock.stock_location_customers')
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        intercom_location = self.env.ref('stock.stock_location_inter_wh')
        intercom_location.write({'active': True})
        partner = self.env['res.partner'].create({'name': 'Deco Addict'})
        self.warehouse_a.resupply_wh_ids = [(6, 0, [self.warehouse_b.id])]
        resupply_route = self.env['stock.location.route'].search([('supplier_wh_id', '=', self.warehouse_b.id),
                                                                  ('supplied_wh_id', '=', self.warehouse_a.id)])
        self.assertTrue(resupply_route, "Resupply route not found")

        product_lot = self.env['product.product'].create({
            'type': 'product',
            'tracking': 'lot',
            'name': 'product lot',
            'route_ids': [(4, resupply_route.id), (4, self.env.ref('stock.route_warehouse0_mto').id)],
        })

        move_sup_to_whb = self.env['stock.move'].create({
            'company_id': self.company_b.id,
            'name': 'from_supplier_to_whb',
            'location_id': supplier_location.id,
            'location_dest_id': self.warehouse_b.lot_stock_id.id,
            'product_id': product_lot.id,
            'product_uom': product_lot.uom_id.id,
            'product_uom_qty': 1.0,
            'picking_type_id': self.warehouse_b.in_type_id.id,
        })
        move_sup_to_whb._action_confirm()
        move_line_1 = move_sup_to_whb.move_line_ids[0]
        move_line_1.lot_name = 'lot b'
        move_line_1.qty_done = 1.0
        move_sup_to_whb._action_done()
        lot_b = move_line_1.lot_id

        picking_out = self.env['stock.picking'].create({
            'company_id': self.company_a.id,
            'partner_id': partner.id,
            'picking_type_id': self.warehouse_a.out_type_id.id,
            'location_id': self.stock_location_a.id,
            'location_dest_id': customer_location.id,
        })
        move_wha_to_cus = self.env['stock.move'].create({
            'name': "WH_A to Customer",
            'product_id': product_lot.id,
            'product_uom_qty': 1,
            'product_uom': product_lot.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location_a.id,
            'location_dest_id': customer_location.id,
            'warehouse_id': self.warehouse_a.id,
            'procure_method': 'make_to_order',
            'company_id': self.company_a.id,
        })
        picking_out.action_confirm()

        move_whb_to_transit = self.env['stock.move'].search([('location_id', '=', self.stock_location_b.id),
                                                             ('product_id', '=', product_lot.id)])
        move_transit_to_wha = self.env['stock.move'].search([('location_id', '=', intercom_location.id),
                                                             ('product_id', '=', product_lot.id)])
        self.assertTrue(move_whb_to_transit, "No move created by pull rule")
        self.assertTrue(move_transit_to_wha, "No move created by pull rule")
        self.assertTrue(move_wha_to_cus in move_transit_to_wha.move_dest_ids,
                        "Moves are not chained")
        self.assertFalse(move_transit_to_wha in move_whb_to_transit.move_dest_ids,
                         "Chained move created in transit location")
        self.assertEqual(move_wha_to_cus.state, "waiting")
        self.assertEqual(move_transit_to_wha.state, "waiting")
        self.assertEqual(move_whb_to_transit.state, "assigned")

        (move_wha_to_cus + move_whb_to_transit + move_transit_to_wha).picking_id.action_assign()
        self.assertEqual(move_wha_to_cus.state, "waiting")
        self.assertEqual(move_transit_to_wha.state, "assigned")
        self.assertEqual(move_whb_to_transit.state, "assigned")

        res_dict = move_whb_to_transit.picking_id.button_validate()
        self.assertEqual(res_dict.get('res_model'), 'stock.immediate.transfer')
        wizard = Form(self.env[res_dict['res_model']].with_context(res_dict['context'])).save()
        wizard.process()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product_lot, intercom_location, lot_b), 1.0)
        with self.assertRaises(UserError):
            move_transit_to_wha.picking_id.button_validate()

        move_line_2 = move_transit_to_wha.move_line_ids[0]
        move_line_2.lot_name = 'lot a'
        move_line_2.qty_done = 1.0
        move_transit_to_wha._action_done()
        lot_a = move_line_2.lot_id

        move_wha_to_cus._action_assign()
        self.assertEqual(move_wha_to_cus.state, "assigned")
        res_dict = move_wha_to_cus.picking_id.button_validate()
        self.assertEqual(res_dict.get('res_model'), 'stock.immediate.transfer')
        wizard = Form(self.env[res_dict['res_model']].with_context(res_dict['context'])).save()
        wizard.process()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product_lot, customer_location, lot_a), 1.0)

        self.assertEqual(lot_a.company_id, self.company_a)
        self.assertEqual(lot_a.name, 'lot a')
        self.assertEqual(lot_b.company_id, self.company_b)
        self.assertEqual(lot_b.name, 'lot b')
