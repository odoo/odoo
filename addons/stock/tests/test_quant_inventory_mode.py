# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import SavepointCase
from odoo.exceptions import AccessError, UserError


class TestEditableQuant(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestEditableQuant, cls).setUpClass()

        # Shortcut to call `stock.quant` with `inventory mode` set in the context
        cls.Quant = cls.env['stock.quant'].with_context(inventory_mode=True)

        Product = cls.env['product.product']
        Location = cls.env['stock.location']
        cls.product = Product.create({
            'name': 'Product A',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.product2 = Product.create({
            'name': 'Product B',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.product_tracked_sn = Product.create({
            'name': 'Product tracked by SN',
            'type': 'product',
            'tracking': 'serial',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.warehouse = Location.create({
            'name': 'Warehouse',
            'usage': 'internal',
        })
        cls.stock = Location.create({
            'name': 'Stock',
            'usage': 'internal',
            'location_id': cls.warehouse.id,
        })
        cls.room1 = Location.create({
            'name': 'Room A',
            'usage': 'internal',
            'location_id': cls.stock.id,
        })
        cls.room2 = Location.create({
            'name': 'Room B',
            'usage': 'internal',
            'location_id': cls.stock.id,
        })
        cls.inventory_loss = cls.product.property_stock_inventory

    def test_create_quant_1(self):
        """ Create a new quant who don't exist yet.
        """
        # Checks we don't have any quant for this product.
        quants = self.env['stock.quant'].search([('product_id', '=', self.product.id)])
        self.assertEqual(len(quants), 0)
        self.Quant.create({
            'product_id': self.product.id,
            'location_id': self.stock.id,
            'inventory_quantity': 24
        })
        quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product.id),
            ('quantity', '>', 0),
        ])
        # Checks we have now a quant, and also checks the quantity is equals to
        # what we set in `inventory_quantity` field.
        self.assertEqual(len(quants), 1)
        self.assertEqual(quants.quantity, 24)

        stock_move = self.env['stock.move'].search([
            ('product_id', '=', self.product.id),
        ])
        self.assertEqual(stock_move.location_id.id, self.inventory_loss.id)
        self.assertEqual(stock_move.location_dest_id.id, self.stock.id)

    def test_create_quant_2(self):
        """ Try to create a quant who already exist.
        Must update the existing quant instead of creating a new one.
        """
        # Creates a quants...
        first_quant = self.Quant.create({
            'product_id': self.product.id,
            'location_id': self.room1.id,
            'quantity': 12,
        })
        quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product.id),
            ('quantity', '>', 0),
        ])
        self.assertEqual(len(quants), 1)
        # ... then try to create an another quant for the same product/location.
        second_quant = self.Quant.create({
            'product_id': self.product.id,
            'location_id': self.room1.id,
            'inventory_quantity': 24,
        })
        quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product.id),
            ('quantity', '>', 0),
        ])
        # Checks we still have only one quant, and first quant quantity was
        # updated, and second quant had the same ID than the first quant.
        self.assertEqual(len(quants), 1)
        self.assertEqual(first_quant.quantity, 24)
        self.assertEqual(first_quant.id, second_quant.id)
        stock_move = self.env['stock.move'].search([
            ('product_id', '=', self.product.id),
        ])
        self.assertEqual(len(stock_move), 1)

    def test_create_quant_3(self):
        """ Try to create a quant with `inventory_quantity` but not in inventory mode.
        Creates two quants not in inventory mode:
          - One with `quantity` (this one must be OK)
          - One with `inventory_quantity` (this one must be null)
        """
        valid_quant = self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.room1.id,
            'quantity': 10,
        })
        invalid_quant = self.env['stock.quant'].create({
            'product_id': self.product2.id,
            'location_id': self.room1.id,
            'inventory_quantity': 20,
        })
        self.assertEqual(valid_quant.quantity, 10)
        self.assertEqual(invalid_quant.quantity, 0)

    def test_create_quant_4(self):
        """ Try to create tree quants in inventory mode with `quantity` and/or `inventory_quantity`.
        Creates two quants not in inventory mode:
          - One with `quantity` (this one must be OK, but `inventory_mode` is useless here as it
            doesn't enter in the inventory mode case and create quant as usual)
          - One with `inventory_quantity` (this one must be OK)
          - One with the two values (this one must raises an error as it enters in the inventory
            mode but user can't edit directly `quantity` in inventory mode)
        """
        valid_quant = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'location_id': self.room1.id,
            'quantity': 10,
        })
        inventoried_quant = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product2.id,
            'location_id': self.room1.id,
            'inventory_quantity': 20,
        })
        with self.assertRaises(UserError):
            invalid_quant = self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': self.product.id,
                'location_id': self.room2.id,
                'quantity': 10,
                'inventory_quantity': 20,
            })
        self.assertEqual(valid_quant.quantity, 10)
        self.assertEqual(inventoried_quant.quantity, 20)

    def test_edit_quant_1(self):
        """ Increases manually quantity of a quant.
        """
        quant = self.Quant.create({
            'product_id': self.product.id,
            'location_id': self.room1.id,
            'quantity': 12,
        })
        quant.inventory_quantity = 24
        self.assertEqual(quant.quantity, 24)
        stock_move = self.env['stock.move'].search([
            ('product_id', '=', self.product.id),
        ])
        self.assertEqual(stock_move.location_id.id, self.inventory_loss.id)
        self.assertEqual(stock_move.location_dest_id.id, self.room1.id)

    def test_edit_quant_2(self):
        """ Decreases manually quantity of a quant.
        """
        quant = self.Quant.create({
            'product_id': self.product.id,
            'location_id': self.room1.id,
            'quantity': 12,
        })
        quant.inventory_quantity = 8
        self.assertEqual(quant.quantity, 8)
        stock_move = self.env['stock.move'].search([
            ('product_id', '=', self.product.id),
        ])
        self.assertEqual(stock_move.location_id.id, self.room1.id)
        self.assertEqual(stock_move.location_dest_id.id, self.inventory_loss.id)

    def test_edit_quant_3(self):
        """ Try to edit a record without the inventory mode.
        Must raise an error.
        """
        self.demo_user = self.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True}).create({
            'name': 'Pauline Poivraisselle',
            'login': 'pauline',
            'email': 'p.p@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
        })
        user_admin = self.env.ref('base.user_admin')
        quant = self.Quant.create({
            'product_id': self.product.id,
            'location_id': self.room1.id,
            'quantity': 12
        })
        self.assertEqual(quant.quantity, 12)
        # Try to write on quant without permission
        with self.assertRaises(AccessError):
            quant.with_user(self.demo_user).write({'inventory_quantity': 8})
        self.assertEqual(quant.quantity, 12)

        # Try to write on quant with permission
        quant.with_user(user_admin).write({'inventory_quantity': 8})
        self.assertEqual(quant.quantity, 8)
