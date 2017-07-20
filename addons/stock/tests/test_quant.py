# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError, UserError


class StockQuant(TransactionCase):
    def setUp(self):
        super(StockQuant, self).setUp()
        Users = self.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True})
        self.demo_user = Users.create({
            'name': 'Pauline Poivraisselle',
            'login': 'pauline',
            'email': 'p.p@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
        })
        self.stock_user = Users.create({
            'name': 'Pauline Poivraisselle',
            'login': 'pauline2',
            'email': 'p.p@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [self.env.ref('stock.group_stock_user').id])]
        })

    def test_get_available_quantity_1(self):
        """ Quantity availability with only one quant in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 1.0,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 1.0)

    def test_get_available_quantity_2(self):
        """ Quantity availability with multiple quants in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        for i in range(3):
            self.env['stock.quant'].create({
                'product_id': product1.id,
                'location_id': stock_location.id,
                'quantity': 1.0,
            })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 3.0)

    def test_get_available_quantity_3(self):
        """ Quantity availability with multiple quants (including negatives ones) in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        for i in range(3):
            self.env['stock.quant'].create({
                'product_id': product1.id,
                'location_id': stock_location.id,
                'quantity': 1.0,
            })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': -3.0,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 0.0)

    def test_get_available_quantity_4(self):
        """ Quantity availability with no quants in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 0.0)

    def test_get_available_quantity_5(self):
        """ Quantity availability with multiple partially reserved quants in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 10.0,
            'reserved_quantity': 9.0,
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 1.0,
            'reserved_quantity': 1.0,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 1.0)

    def test_get_available_quantity_6(self):
        """ Quantity availability with multiple partially reserved quants in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 10.0,
            'reserved_quantity': 20.0,
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 5.0,
            'reserved_quantity': 0.0,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), -5.0)

    def test_get_available_quantity_7(self):
        """ Quantity availability with only one tracked quant in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'tracking': 'lot',
        })
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': product1.id,
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 10.0,
            'reserved_quantity': 20.0,
            'lot_id': lot1.id,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location, lot_id=lot1), -10.0)

    def test_get_available_quantity_8(self):
        """ Quantity availability with a consumable product.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'consu',
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(product1, stock_location)), 0)
        with self.assertRaises(ValidationError):
            self.env['stock.quant']._update_available_quantity(product1, stock_location, 1.0)

    def test_get_available_quantity_9(self):
        """ Quantity availability by a demo user with access rights/rules.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 1.0,
        })
        self.env = self.env(user=self.env.ref('base.user_demo'))
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 1.0)

    def test_increase_available_quantity_1(self):
        """ Increase the available quantity when no quants are already in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant']._update_available_quantity(product1, stock_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 1.0)

    def test_increase_available_quantity_2(self):
        """ Increase the available quantity when multiple quants are already in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        for i in range(2):
            self.env['stock.quant'].create({
                'product_id': product1.id,
                'location_id': stock_location.id,
                'quantity': 1.0,
            })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 2.0)
        self.env['stock.quant']._update_available_quantity(product1, stock_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 3.0)
        self.assertEqual(len(self.env['stock.quant']._gather(product1, stock_location)), 2)

    def test_increase_available_quantity_3(self):
        """ Increase the available quantity when a concurrent transaction is already increasing
        the reserved quanntity for the same product.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product = self.env.ref('stock.test_quant_product')
        product.type = 'product'  # product 12 is a consumable by default
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product, stock_location), 10.0)

        # opens a new cursor and SELECT FOR UPDATE the quant, to simulate another concurrent reserved
        # quantity increase
        cr2 = self.registry.cursor()
        cr2.execute("SELECT id FROM stock_quant WHERE product_id=%s AND location_id=%s", (product.id, stock_location.id))
        quant_id = cr2.fetchone()
        cr2.execute("SELECT 1 FROM stock_quant WHERE id=%s FOR UPDATE", quant_id)

        self.env['stock.quant']._update_available_quantity(product, stock_location, 1.0)
        cr2.rollback()
        cr2.close()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product, stock_location), 11.0)
        self.assertEqual(len(self.env['stock.quant']._gather(product, stock_location)), 2)

    def test_increase_available_quantity_4(self):
        """ Increase the available quantity when no quants are already in a location with a user without access right.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env = self.env(user=self.env.ref('base.user_demo'))
        self.env['stock.quant']._update_available_quantity(product1, stock_location, 1.0)

    def test_increase_available_quantity_5(self):
        """ Increase the available quantity when no quants are already in stock.
        Increase a subLocation and check that quants are in this location. Also test inverse.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        stock_sub_location = stock_location.child_ids[0]
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        product2 = self.env['product.product'].create({
            'name': 'Product B',
            'type': 'product',
        })
        self.env['stock.quant']._update_available_quantity(product1, stock_location, 1.0)
        self.env['stock.quant']._update_available_quantity(product1, stock_sub_location, 1.0)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_sub_location), 1.0)

        self.env['stock.quant']._update_available_quantity(product2, stock_sub_location, 1.0)
        self.env['stock.quant']._update_available_quantity(product2, stock_location, 1.0)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(product2, stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product2, stock_sub_location), 1.0)

    def test_decrease_available_quantity_1(self):
        """ Decrease the available quantity when no quants are already in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant']._update_available_quantity(product1, stock_location, -1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), -1.0)

    def test_decrease_available_quantity_2(self):
        """ Decrease the available quantity when multiple quants are already in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        for i in range(2):
            self.env['stock.quant'].create({
                'product_id': product1.id,
                'location_id': stock_location.id,
                'quantity': 1.0,
            })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 2.0)
        self.assertEqual(len(self.env['stock.quant']._gather(product1, stock_location)), 2)
        self.env['stock.quant']._update_available_quantity(product1, stock_location, -1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(product1, stock_location)), 1)

    def test_decrease_available_quantity_3(self):
        """ Decrease the available quantity when a concurrent transaction is already increasing
        the reserved quanntity for the same product.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product = self.env.ref('stock.test_quant_product')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product, stock_location), 10.0)
        quants = self.env['stock.quant']._gather(product, stock_location)
        self.assertEqual(len(quants), 1)

        # opens a new cursor and SELECT FOR UPDATE the quant, to simulate another concurrent reserved
        # quantity increase
        cr2 = self.registry.cursor()
        cr2.execute("SELECT 1 FROM stock_quant WHERE id = %s FOR UPDATE", quants.ids)
        self.env['stock.quant']._update_available_quantity(product, stock_location, -1.0)
        cr2.rollback()
        cr2.close()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product, stock_location), 9.0)
        self.assertEqual(len(self.env['stock.quant']._gather(product, stock_location)), 2)

    def test_decrease_available_quantity_4(self):
        """ Decrease the available quantity that delete the quant. The active user should have
        read,write and unlink rights
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 1.0,
        })
        self.env = self.env(user=self.demo_user)
        self.env['stock.quant']._update_available_quantity(product1, stock_location, -1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(product1, stock_location)), 0)

    def test_increase_reserved_quantity_1(self):
        """ Increase the reserved quantity of quantity x when there's a single quant in a given
        location which has an available quantity of x.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 10.0,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 10.0)
        self.assertEqual(len(self.env['stock.quant']._gather(product1, stock_location)), 1)
        self.env['stock.quant']._update_reserved_quantity(product1, stock_location, 10.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(product1, stock_location)), 1)

    def test_increase_reserved_quantity_2(self):
        """ Increase the reserved quantity of quantity x when there's two quants in a given
        location which have an available quantity of x together.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        for i in range(2):
            self.env['stock.quant'].create({
                'product_id': product1.id,
                'location_id': stock_location.id,
                'quantity': 5.0,
            })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 10.0)
        self.assertEqual(len(self.env['stock.quant']._gather(product1, stock_location)), 2)
        self.env['stock.quant']._update_reserved_quantity(product1, stock_location, 10.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(product1, stock_location)), 2)

    def test_increase_reserved_quantity_3(self):
        """ Increase the reserved quantity of quantity x when there's multiple quants in a given
        location which have an available quantity of x together.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 5.0,
            'reserved_quantity': 2.0,
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 10.0,
            'reserved_quantity': 12.0,
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 8.0,
            'reserved_quantity': 3.0,
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 35.0,
            'reserved_quantity': 12.0,
        })
        # total quantity: 58
        # total reserved quantity: 29
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 29.0)
        self.assertEqual(len(self.env['stock.quant']._gather(product1, stock_location)), 4)
        self.env['stock.quant']._update_reserved_quantity(product1, stock_location, 10.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 19.0)
        self.assertEqual(len(self.env['stock.quant']._gather(product1, stock_location)), 4)

    def test_increase_reserved_quantity_4(self):
        """ Increase the reserved quantity of quantity x when there's multiple quants in a given
        location which have an available quantity of x together.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 5.0,
            'reserved_quantity': 7.0,
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 12.0,
            'reserved_quantity': 10.0,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(product1, stock_location)), 2)
        with self.assertRaises(UserError):
            self.env['stock.quant']._update_reserved_quantity(product1, stock_location, 10.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 0.0)

    def test_increase_reserved_quantity_5(self):
        """ Decrease the available quantity when no quant are in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        with self.assertRaises(UserError):
            self.env['stock.quant']._update_reserved_quantity(product1, stock_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 0.0)

    def test_decrease_reserved_quantity_1(self):
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 10.0,
            'reserved_quantity': 10.0,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(product1, stock_location)), 1)
        self.env['stock.quant']._update_reserved_quantity(product1, stock_location, -10.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 10.0)
        self.assertEqual(len(self.env['stock.quant']._gather(product1, stock_location)), 1)

    def test_increase_decrease_reserved_quantity_1(self):
        """ Decrease then increase reserved quantity when no quant are in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        with self.assertRaises(UserError):
            self.env['stock.quant']._update_reserved_quantity(product1, stock_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 0.0)
        with self.assertRaises(UserError):
            self.env['stock.quant']._update_reserved_quantity(product1, stock_location, -1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 0.0)

    def test_action_done_1(self):
        stock_location = self.env.ref('stock.stock_location_stock')
        pack_location = self.env.ref('stock.location_pack_zone')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant']._update_available_quantity(product1, stock_location, 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 2.0)
        self.env['stock.quant']._update_reserved_quantity(product1, stock_location, 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 0.0)
        self.env['stock.quant']._update_reserved_quantity(product1, stock_location, -2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 2.0)
        self.env['stock.quant']._update_available_quantity(product1, stock_location, -2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 0.0)
        self.env['stock.quant']._update_available_quantity(product1, pack_location, 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, pack_location), 2.0)

    def test_mix_tracked_untracked_1(self):
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'tracking': 'serial',
        })
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': product1.id,
        })

        # add one tracked, one untracked
        self.env['stock.quant']._update_available_quantity(product1, stock_location, 1.0)
        self.env['stock.quant']._update_available_quantity(product1, stock_location, 1.0, lot_id=lot1)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location, strict=True), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location, lot_id=lot1), 1.0)

        self.env['stock.quant']._update_reserved_quantity(product1, stock_location, 1.0, lot_id=lot1, strict=True)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location, strict=True), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location, lot_id=lot1), 0.0)

        self.env['stock.quant']._update_reserved_quantity(product1, stock_location, -1.0, lot_id=lot1, strict=True)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location, strict=True), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location, lot_id=lot1), 1.0)

        with self.assertRaises(UserError):
            self.env['stock.quant']._update_reserved_quantity(product1, stock_location, -1.0)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location, strict=True), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location, lot_id=lot1), 1.0)

    def test_access_rights_1(self):
        """ Directly update the quant with a user with or without stock access rights sould raise
        an AccessError.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        quant = self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 1.0,
        })
        self.env = self.env(user=self.demo_user)
        with self.assertRaises(AccessError):
            self.env['stock.quant'].create({
                'product_id': product1.id,
                'location_id': stock_location.id,
                'quantity': 1.0,
            })
        with self.assertRaises(AccessError):
            quant.sudo(self.demo_user).write({'quantity': 2.0})
        with self.assertRaises(AccessError):
            quant.sudo(self.demo_user).unlink()

        self.env = self.env(user=self.stock_user)
        with self.assertRaises(AccessError):
            self.env['stock.quant'].create({
                'product_id': product1.id,
                'location_id': stock_location.id,
                'quantity': 1.0,
            })
        with self.assertRaises(AccessError):
            quant.sudo(self.demo_user).write({'quantity': 2.0})
        with self.assertRaises(AccessError):
            quant.sudo(self.demo_user).unlink()
