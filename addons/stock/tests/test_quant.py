# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from contextlib import closing
from datetime import datetime, timedelta
from unittest.mock import patch
from ast import literal_eval

from odoo import Command, fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import ValidationError
from odoo.tests import Form, TransactionCase
from odoo.exceptions import AccessError, UserError


class StockQuant(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(StockQuant, cls).setUpClass()
        cls.demo_user = mail_new_test_user(
            cls.env,
            name='Pauline Poivraisselle',
            login='pauline',
            email='p.p@example.com',
            notification_type='inbox',
            groups='base.group_user',
        )
        cls.stock_user = mail_new_test_user(
            cls.env,
            name='Pauline Poivraisselle',
            login='pauline2',
            email='p.p@example.com',
            notification_type='inbox',
            groups='stock.group_stock_user',
        )

        cls.product = cls.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
        })
        cls.product_lot = cls.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'tracking': 'lot',
        })
        cls.product_consu = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'consu',
        })
        cls.product_serial = cls.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'tracking': 'serial',
        })
        cls.stock_location = cls.env['stock.location'].create({
            'name': 'stock_location',
            'usage': 'internal',
        })
        cls.stock_subloc3 = cls.env['stock.location'].create({
            'name': 'subloc3',
            'usage': 'internal',
            'location_id': cls.stock_location.id
        })
        cls.stock_subloc2 = cls.env['stock.location'].create({
            'name': 'subloc2',
            'usage': 'internal',
            'location_id': cls.stock_location.id,
        })

    def gather_relevant(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        quants = self.env['stock.quant']._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
        return quants.filtered(lambda q: not (q.quantity == 0 and q.reserved_quantity == 0))

    def test_copy_quant(self):
        """
        You should not be allowed to duplicate quants.
        """
        quant = self.env['stock.quant'].create([{
            'location_id': self.stock_location.id,
            'product_id': self.product.id,
            'inventory_quantity': 10,
        }])
        with self.assertRaises(UserError):
            quant.copy()

    def test_get_available_quantity_1(self):
        """ Quantity availability with only one quant in a location.
        """
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 1.0,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)

    def test_get_available_quantity_2(self):
        """ Quantity availability with multiple quants in a location.
        """
        for i in range(3):
            self.env['stock.quant'].create({
                'product_id': self.product.id,
                'location_id': self.stock_location.id,
                'quantity': 1.0,
            })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 3.0)

    def test_get_available_quantity_3(self):
        """ Quantity availability with multiple quants (including negatives ones) in a location.
        """
        for i in range(3):
            self.env['stock.quant'].create({
                'product_id': self.product.id,
                'location_id': self.stock_location.id,
                'quantity': 1.0,
            })
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': -3.0,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)

    def test_get_available_quantity_4(self):
        """ Quantity availability with no quants in a location.
        """
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)

    def test_get_available_quantity_5(self):
        """ Quantity availability with multiple partially reserved quants in a location.
        """
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 10.0,
            'reserved_quantity': 9.0,
        })
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 1.0,
            'reserved_quantity': 1.0,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)

    def test_get_available_quantity_6(self):
        """ Quantity availability with multiple partially reserved quants in a location.
        """
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 10.0,
            'reserved_quantity': 20.0,
        })
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 5.0,
            'reserved_quantity': 0.0,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, allow_negative=True), -5.0)

    def test_get_available_quantity_7(self):
        """ Quantity availability with only one tracked quant in a location.
        """
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.product_lot.id,
        })
        self.env['stock.quant'].create({
            'product_id': self.product_lot.id,
            'location_id': self.stock_location.id,
            'quantity': 10.0,
            'reserved_quantity': 20.0,
            'lot_id': lot1.id,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location, lot_id=lot1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location, lot_id=lot1, allow_negative=True), -10.0)

    def test_get_available_quantity_8(self):
        """ Quantity availability with a consumable product.
        """
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_consu, self.stock_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product_consu, self.stock_location)), 0)
        with self.assertRaises(ValidationError):
            self.env['stock.quant']._update_available_quantity(self.product_consu, self.stock_location, 1.0)

    def test_get_available_quantity_9(self):
        """ Quantity availability by a demo user with access rights/rules.
        """
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 1.0,
        })
        self.env = self.env(user=self.demo_user)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)

    def test_increase_available_quantity_1(self):
        """ Increase the available quantity when no quants are already in a location.
        """
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)

    def test_increase_available_quantity_2(self):
        """ Increase the available quantity when multiple quants are already in a location.
        """
        for i in range(2):
            self.env['stock.quant'].create({
                'product_id': self.product.id,
                'location_id': self.stock_location.id,
                'quantity': 1.0,
            })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 3.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 2)

    def test_increase_available_quantity_3(self):
        """ Increase the available quantity when a concurrent transaction is already increasing
        the reserved quanntity for the same product.
        """
        quant = self.env['stock.quant'].search([('location_id', '=', self.stock_location.id)], limit=1)
        if not quant:
            self.skipTest('Cannot test concurrent transactions without demo data.')
        product = quant.product_id
        available_quantity = self.env['stock.quant']._get_available_quantity(product, self.stock_location, allow_negative=True)
        # opens a new cursor and SELECT FOR UPDATE the quant, to simulate another concurrent reserved
        # quantity increase
        with closing(self.registry.cursor()) as cr:
            cr.execute("SELECT id FROM stock_quant WHERE product_id=%s AND location_id=%s", (product.id, self.stock_location.id))
            quant_id = cr.fetchone()
            cr.execute("SELECT 1 FROM stock_quant WHERE id=%s FOR UPDATE", quant_id)
            self.env['stock.quant']._update_available_quantity(product, self.stock_location, 1.0)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(product, self.stock_location, allow_negative=True), available_quantity + 1)
        self.assertEqual(len(self.gather_relevant(product, self.stock_location, strict=True)), 2)

    def test_increase_available_quantity_4(self):
        """ Increase the available quantity when no quants are already in a location with a user without access right.
        """
        self.env = self.env(user=self.demo_user)
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0)

    def test_increase_available_quantity_5(self):
        """ Increase the available quantity when no quants are already in stock.
        Increase a subLocation and check that quants are in this location. Also test inverse.
        """
        stock_sub_location = self.stock_location.child_ids[0]
        product2 = self.env['product.product'].create({
            'name': 'Product B',
            'is_storable': True,
        })
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0)
        self.env['stock.quant']._update_available_quantity(self.product, stock_sub_location, 1.0)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, stock_sub_location), 1.0)

        self.env['stock.quant']._update_available_quantity(product2, stock_sub_location, 1.0)
        self.env['stock.quant']._update_available_quantity(product2, self.stock_location, 1.0)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(product2, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product2, stock_sub_location), 1.0)

    def test_increase_available_quantity_6(self):
        """ Increasing the available quantity in a view location should be forbidden.
        """
        location1 = self.env['stock.location'].create({
            'name': 'viewloc1',
            'usage': 'view',
            'location_id': self.stock_location.id,
        })
        with self.assertRaises(ValidationError):
            self.env['stock.quant']._update_available_quantity(self.product, location1, 1.0)

    def test_increase_available_quantity_7(self):
        """ Setting a location's usage as "view" should be forbidden if it already
        contains quant.
        """
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0)
        self.assertTrue(len(self.stock_location.quant_ids.ids) > 0)
        with self.assertRaises(UserError):
            self.stock_location.usage = 'view'

    def test_decrease_available_quantity_1(self):
        """ Decrease the available quantity when no quants are already in a location.
        """
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, -1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, allow_negative=True), -1.0)

    def test_decrease_available_quantity_2(self):
        """ Decrease the available quantity when multiple quants are already in a location.
        """
        for i in range(2):
            self.env['stock.quant'].create({
                'product_id': self.product.id,
                'location_id': self.stock_location.id,
                'quantity': 1.0,
            })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 2)
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, -1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1)

    def test_decrease_available_quantity_3(self):
        """ Decrease the available quantity when a concurrent transaction is already increasing
        the reserved quanntity for the same product.
        """
        quant = self.env['stock.quant'].search([('location_id', '=', self.stock_location.id)], limit=1)
        if not quant:
            self.skipTest('Cannot test concurrent transactions without demo data.')
        product = quant.product_id
        available_quantity = self.env['stock.quant']._get_available_quantity(product, self.stock_location, allow_negative=True)

        # opens a new cursor and SELECT FOR UPDATE the quant, to simulate another concurrent reserved
        # quantity increase
        with closing(self.registry.cursor()) as cr:
            cr.execute("SELECT 1 FROM stock_quant WHERE id = %s FOR UPDATE", quant.ids)
            self.env['stock.quant']._update_available_quantity(product, self.stock_location, -1.0)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(product, self.stock_location, allow_negative=True), available_quantity - 1)
        self.assertEqual(len(self.gather_relevant(product, self.stock_location, strict=True)), 2)

    def test_decrease_available_quantity_4(self):
        """ Decrease the available quantity that delete the quant. The active user should have
        read,write and unlink rights
        """
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 1.0,
        })
        self.env = self.env(user=self.demo_user)
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, -1.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 0)

    def test_increase_reserved_quantity_1(self):
        """ Increase the reserved quantity of quantity x when there's a single quant in a given
        location which has an available quantity of x.
        """
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 10.0,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 10.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1)
        self.env['stock.quant']._update_reserved_quantity(self.product, self.stock_location, 10.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1)

    def test_increase_reserved_quantity_2(self):
        """ Increase the reserved quantity of quantity x when there's two quants in a given
        location which have an available quantity of x together.
        """
        for i in range(2):
            self.env['stock.quant'].create({
                'product_id': self.product.id,
                'location_id': self.stock_location.id,
                'quantity': 5.0,
            })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 10.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 2)
        self.env['stock.quant']._update_reserved_quantity(self.product, self.stock_location, 10.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 2)

    def test_increase_reserved_quantity_3(self):
        """ Increase the reserved quantity of quantity x when there's multiple quants in a given
        location which have an available quantity of x together.
        """
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 5.0,
            'reserved_quantity': 2.0,
        })
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 10.0,
            'reserved_quantity': 12.0,
        })
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 8.0,
            'reserved_quantity': 3.0,
        })
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 35.0,
            'reserved_quantity': 12.0,
        })
        # total quantity: 58
        # total reserved quantity: 29
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 29.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 4)
        self.env['stock.quant']._update_reserved_quantity(self.product, self.stock_location, 10.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 19.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 4)

    def test_increase_reserved_quantity_4(self):
        """ Increase the reserved quantity of quantity x when there's multiple quants in a given
        location which have an available quantity of x together.
        """
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 5.0,
            'reserved_quantity': 7.0,
        })
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 12.0,
            'reserved_quantity': 10.0,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 2)
        reserved_quants = self.env['stock.quant']._update_reserved_quantity(self.product, self.stock_location, 10.0)
        self.assertFalse(reserved_quants)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)

    def test_increase_reserved_quantity_5(self):
        """ Decrease the available quantity when no quant are in a location.
        """
        reserved_quants = self.env['stock.quant']._update_reserved_quantity(self.product, self.stock_location, 1.0)
        self.assertFalse(reserved_quants)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)

    def test_decrease_reserved_quantity_1(self):
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 10.0,
            'reserved_quantity': 10.0,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1)
        self.env['stock.quant']._update_reserved_quantity(self.product, self.stock_location, -10.0, strict=True)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 10.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1)

    def test_action_done_1(self):
        pack_location = self.env.ref('stock.location_pack_zone')
        pack_location.active = True
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)
        self.env['stock.quant']._update_reserved_quantity(self.product, self.stock_location, 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        self.env['stock.quant']._update_reserved_quantity(self.product, self.stock_location, -2.0, strict=True)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, -2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        self.env['stock.quant']._update_available_quantity(self.product, pack_location, 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, pack_location), 2.0)

    def test_mix_tracked_untracked_1(self):
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.product_serial.id,
        })

        # add one tracked, one untracked
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0)
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0, lot_id=lot1)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, strict=True), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot1), 2.0)

        self.env['stock.quant']._update_reserved_quantity(self.product_serial, self.stock_location, 1.0, lot_id=lot1, strict=True)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, strict=True), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot1), 1.0)

        self.env['stock.quant']._update_reserved_quantity(self.product_serial, self.stock_location, -1.0, lot_id=lot1, strict=True)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, strict=True), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot1), 2.0)

    def test_access_rights_1(self):
        """ Directly update the quant with a user with or without stock access rights should not raise
        an AccessError only deletion will.
        """
        quant = self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 1.0,
        })
        self.env = self.env(user=self.demo_user)
        with self.assertRaises(AccessError):
            self.env['stock.quant'].create({
                'product_id': self.product.id,
                'location_id': self.stock_location.id,
                'quantity': 1.0,
            })
        with self.assertRaises(AccessError):
            quant.with_user(self.demo_user).write({'quantity': 2.0})
        with self.assertRaises(UserError):
            quant.with_user(self.demo_user).unlink()

        self.env = self.env(user=self.stock_user)
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 1.0,
        })
        quant.with_user(self.stock_user).with_context(inventory_mode=True).write({'quantity': 3.0})
        with self.assertRaises(AccessError):
            quant.with_user(self.stock_user).unlink()

    def test_quant_in_date_1(self):
        """ Check that no incoming date is set when updating the quantity of an untracked quant.
        """
        quantity, in_date = self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0)
        self.assertEqual(quantity, 1)
        self.assertNotEqual(in_date, None)

    def test_quant_in_date_1b(self):
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 1.0,
        })
        quantity, in_date = self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 2.0)
        self.assertEqual(quantity, 3)
        self.assertNotEqual(in_date, None)

    def test_quant_in_date_2(self):
        """ Check that an incoming date is correctly set when updating the quantity of a tracked
        quant.
        """
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.product_serial.id,
        })
        quantity, in_date = self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0, lot_id=lot1)
        self.assertEqual(quantity, 1)
        self.assertNotEqual(in_date, None)

    def test_quant_in_date_3(self):
        """ Check that the FIFO strategies correctly applies when you have multiple lot received
        at different times for a tracked product.
        """
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.product_serial.id,
        })
        lot2 = self.env['stock.lot'].create({
            'name': 'lot2',
            'product_id': self.product_serial.id,
        })
        in_date_lot1 = datetime.now()
        in_date_lot2 = datetime.now() - timedelta(days=5)
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0, lot_id=lot1, in_date=in_date_lot1)
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0, lot_id=lot2, in_date=in_date_lot2)
        quants = self.env['stock.quant']._get_reserve_quantity(self.product_serial, self.stock_location, 1.0)

        # Default removal strategy is FIFO, so lot2 should be received as it was received earlier.
        self.assertEqual(quants[0][0].lot_id.id, lot2.id)

    def test_in_date_4(self):
        """ Check that the LIFO strategies correctly applies when you have multiple lot received
        at different times for a tracked product.
        """
        lifo_strategy = self.env['product.removal'].search([('method', '=', 'lifo')])
        self.stock_location.removal_strategy_id = lifo_strategy
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.product_serial.id,
        })
        lot2 = self.env['stock.lot'].create({
            'name': 'lot2',
            'product_id': self.product_serial.id,
        })
        in_date_lot1 = datetime.now()
        in_date_lot2 = datetime.now() - timedelta(days=5)
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0, lot_id=lot1, in_date=in_date_lot1)
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0, lot_id=lot2, in_date=in_date_lot2)

        self.env['stock.quant']._update_reserved_quantity(self.product_serial, self.stock_location, 1)
        quants = self.env['stock.quant'].search([('product_id', '=', self.product_serial.id), ('location_id', '=', self.stock_location.id)])

        # Removal strategy is LIFO, so lot1 should be received as it was received later.
        self.assertEqual(quants[0][0].lot_id.id, lot1.id)

    def test_quant_in_date_5(self):
        """ Receive the same lot at different times, once they're in the same location, the quants
        are merged and only the earliest incoming date is kept.
        """
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.product_lot.id,
        })

        from odoo.fields import Datetime
        in_date1 = Datetime.now()
        self.env['stock.quant']._update_available_quantity(self.product_lot, self.stock_location, 1.0, lot_id=lot1, in_date=in_date1)

        quant = self.env['stock.quant'].search([
            ('product_id', '=', self.product_lot.id),
            ('location_id', '=', self.stock_location.id),
        ])
        self.assertEqual(len(quant), 1)
        self.assertEqual(quant.quantity, 1)
        self.assertEqual(quant.lot_id.id, lot1.id)
        self.assertEqual(quant.in_date, in_date1)

        in_date2 = Datetime.now() - timedelta(days=5)
        self.env['stock.quant']._update_available_quantity(self.product_lot, self.stock_location, 1.0, lot_id=lot1, in_date=in_date2)

        quant = self.env['stock.quant'].search([
            ('product_id', '=', self.product_lot.id),
            ('location_id', '=', self.stock_location.id),
        ])
        self.assertEqual(len(quant), 1)
        self.assertEqual(quant.quantity, 2)
        self.assertEqual(quant.lot_id.id, lot1.id)
        self.assertEqual(quant.in_date, in_date2)

    def test_closest_removal_strategy_tracked(self):
        """ Check that the Closest location strategy correctly applies when you have multiple lot received
        at different locations for a tracked product.
        """
        # Enable multi-locations to be able to set an origin location for delivery
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [Command.link(grp_multi_loc.id)]})

        closest_strategy = self.env['product.removal'].search([('method', '=', 'closest')])
        self.stock_location.removal_strategy_id = closest_strategy
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.product_serial.id,
        })
        lot2 = self.env['stock.lot'].create({
            'name': 'lot2',
            'product_id': self.product_serial.id,
        })
        in_date = datetime.now()
        # Add a product from lot1 in stock_location/subloc3
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_subloc3, 1.0, lot_id=lot1, in_date=in_date)
        # Add a product from lot2 in stock_location/subloc2
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_subloc2, 1.0, lot_id=lot2, in_date=in_date)
        # Require one unit of the product for a delivery
        with Form(self.env['stock.picking']) as picking_form:
            picking_form.picking_type_id = self.env.ref('stock.picking_type_out')
            picking_form.location_id = self.stock_location
            with picking_form.move_ids_without_package.new() as move_form:
                move_form.product_id = self.product_serial
                move_form.product_uom_qty = 1
            picking = picking_form.save()
        picking.action_confirm()

        # Default removal strategy is 'Closest location', so lot2 should be received as it was put in a closer location. (stock_location/subloc2 < stock_location/subloc3)
        self.assertEqual(picking.move_ids.lot_ids.id, lot2.id)

    def test_closest_removal_strategy_untracked(self):
        """ Check that the Closest location strategy correctly applies when you have multiple products received
        at different locations for untracked products."""
        closest_strategy = self.env['product.removal'].search([('method', '=', 'closest')])
        self.stock_location.removal_strategy_id = closest_strategy
        # Add 2 units of product into stock_location/subloc2
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_subloc2.id,
            'quantity': 2.0,
        })
        # Add 3 units of product into stock_location/subloc3
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_subloc3.id,
            'quantity': 3.0
        })
        # Request 3 units of product, with 'Closest location' as removal strategy
        quants = self.env['stock.quant']._get_reserve_quantity(self.product, self.stock_location, 3)

        # The 2 in stock_location/subloc2 should be taken first, as the location name is smaller alphabetically
        self.assertEqual(quants[0][1], 2)
        self.assertEqual(quants[0][0].location_id, self.stock_subloc2)
        # The last one should then be taken in stock_location/subloc3 since the first location doesn't have enough products
        self.assertEqual(quants[1][1], 1)
        self.assertEqual(quants[1][0].location_id, self.stock_subloc3)

    def test_in_date_6(self):
        """
        One P in stock, P is delivered. Later on, a stock adjustement adds one P. This test checks
        the date value of the related quant
        """
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0)

        move = self.env['stock.move'].create({
            'name': 'OUT 1 product',
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'product_uom': self.product.uom_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
        })
        move._action_confirm()
        move._action_assign()
        move.quantity = 1
        move.picked = True
        move._action_done()

        tomorrow = fields.Datetime.now() + timedelta(days=1)
        with patch.object(fields.Datetime, 'now', lambda: tomorrow):
            move = self.env['stock.move'].create({
                'name': 'IN 1 product',
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'product_uom': self.product.uom_id.id,
                'location_id': self.ref('stock.stock_location_suppliers'),
                'location_dest_id': self.stock_location.id,
            })
            move._action_confirm()
            move._action_assign()
            move.quantity = 1
            move.picked = True
            move._action_done()

            quant = self.env['stock.quant'].search([('product_id', '=', self.product.id), ('location_id', '=', self.stock_location.id), ('quantity', '>', 0)])
            self.assertEqual(quant.in_date, tomorrow)

    def test_quant_creation(self):
        """
        This test ensures that, after an internal transfer, the values of the created quand are correct
        """
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 10.0)

        move = self.env['stock.move'].create({
            'name': 'Move 1 product',
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'product_uom': self.product.uom_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_subloc2.id,
        })
        move._action_confirm()
        move._action_assign()
        move.quantity = 1
        move.picked = True
        move._action_done()

        quant = self.gather_relevant(self.product, self.stock_subloc2)
        self.assertFalse(quant.inventory_quantity_set)

    def test_unpack_and_quants_merging(self):
        """
        When unpacking a package, if there are already some quantities of the
        packed product in the stock, the quant of the on hand quantity and the
        one of the package should be merged
        """
        stock_location = self.env['stock.warehouse'].search([], limit=1).lot_stock_id
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        picking_type_in = self.env.ref('stock.picking_type_in')

        self.env['stock.quant']._update_available_quantity(self.product, stock_location, 1.0)

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type_in.id,
            'location_id': supplier_location.id,
            'location_dest_id': stock_location.id,
            'move_ids': [(0, 0, {
                'name': 'In 10 x %s' % self.product.name,
                'product_id': self.product.id,
                'location_id': supplier_location.id,
                'location_dest_id': stock_location.id,
                'product_uom_qty': 10,
                'product_uom': self.product.uom_id.id,
            })],
            'state': 'draft',
        })
        picking.action_confirm()

        package = self.env['stock.quant.package'].create({
            'name': 'Super Package',
        })
        picking.move_ids.move_line_ids.write({
            'quantity': 10,
            'result_package_id': package.id,
        })
        picking.move_ids.picked = True
        picking.button_validate()

        package.unpack()

        quant = self.env['stock.quant'].search([('product_id', '=', self.product.id), ('on_hand', '=', True)])
        self.assertEqual(len(quant), 1)
        # The quants merging is processed thanks to a SQL query (see StockQuant._merge_quants).
        # At that point, the ORM is not aware of the new value. So we need to invalidate the
        # cache to ensure that the value will be the newest
        quant.invalidate_recordset(['quantity'])
        self.assertEqual(quant.quantity, 11)

    def test_quant_display_name(self):
        """ Check the display name of a quant. """
        self.env.user.groups_id += self.env.ref('stock.group_production_lot')
        sn1 = self.env['stock.lot'].create({
            'name': 'sn1',
            'product_id': self.product_serial.id,
        })
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.product_lot.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0)
        self.env['stock.quant']._update_available_quantity(self.product_lot, self.stock_location, 1.0, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0, lot_id=sn1)
        quants = self.stock_location.quant_ids
        for q in quants:
            if q.lot_id:
                self.assertEqual(q.display_name, '%s - %s' % (q.location_id.display_name, q.lot_id.name))
            else:
                self.assertEqual(q.display_name, '%s' % (q.location_id.display_name))

    def test_serial_constraint_with_package_and_return(self):
        """
        Receive product with serial S
        Return it in a package
        Confirm a new receipt with S
        """
        stock_location = self.env['stock.warehouse'].search([], limit=1).lot_stock_id
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        picking_type_in = self.env.ref('stock.picking_type_in')

        receipt01 = self.env['stock.picking'].create({
            'picking_type_id': picking_type_in.id,
            'location_id': supplier_location.id,
            'location_dest_id': stock_location.id,
            'move_ids': [(0, 0, {
                'name': self.product_serial.name,
                'product_id': self.product_serial.id,
                'location_id': supplier_location.id,
                'location_dest_id': stock_location.id,
                'product_uom_qty': 1,
                'product_uom': self.product_serial.uom_id.id,
            })],
        })
        receipt01.action_confirm()
        receipt01.move_line_ids.write({
            'lot_name': 'Michel',
            'quantity': 1.0
        })
        receipt01.button_validate()

        quant = self.env['stock.quant'].search([('product_id', '=', self.product_serial.id), ('location_id', '=', stock_location.id)])

        wizard_form = Form(self.env['stock.return.picking'].with_context(active_ids=receipt01.ids, active_id=receipt01.ids[0], active_model='stock.picking'))
        wizard = wizard_form.save()
        wizard.product_return_moves.quantity = 1.0
        stock_return_picking_action = wizard.action_create_returns()

        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.move_ids.move_line_ids.quantity = 1.0
        return_pick.action_put_in_pack()
        return_pick.move_ids.picked = True
        return_pick._action_done()

        self.assertEqual(return_pick.move_line_ids.lot_id, quant.lot_id)
        self.assertTrue(return_pick.move_line_ids.result_package_id, quant.lot_id)

        receipt02 = self.env['stock.picking'].create({
            'picking_type_id': picking_type_in.id,
            'location_id': supplier_location.id,
            'location_dest_id': stock_location.id,
            'move_ids': [(0, 0, {
                'name': self.product_serial.name,
                'product_id': self.product_serial.id,
                'location_id': supplier_location.id,
                'location_dest_id': stock_location.id,
                'product_uom_qty': 1,
                'product_uom': self.product_serial.uom_id.id,
            })],
        })
        receipt02.action_confirm()
        receipt02.move_line_ids.write({
            'lot_name': 'Michel',
            'quantity': 1.0
        })
        receipt02.button_validate()

        quant = self.env['stock.quant'].search([('product_id', '=', self.product_serial.id), ('location_id', '=', stock_location.id)])
        self.assertEqual(len(quant), 1)
        self.assertEqual(quant.lot_id.name, 'Michel')

    def test_update_quant_with_forbidden_field(self):
        """
        Test that updating a quant with a forbidden field raise an error.
        """
        product = self.env['product.product'].create({
            'name': 'Product',
            'is_storable': True,
            'tracking': 'serial',
        })
        sn1 = self.env['stock.lot'].create({
            'name': 'SN1',
            'product_id': product.id,
        })
        self.env['stock.quant']._update_available_quantity(product, self.stock_subloc2, 1.0, lot_id=sn1)
        self.assertEqual(len(product.stock_quant_ids), 1)
        self.env['stock.quant']._update_available_quantity(product, self.stock_subloc3, 1.0, lot_id=sn1)
        self.assertEqual(len(product.stock_quant_ids), 2)
        quant_2 = product.stock_quant_ids[1]
        self.assertEqual(quant_2.with_context(inventory_mode=True).sn_duplicated, True)
        with self.assertRaises(UserError):
            quant_2.with_context(inventory_mode=True).write({'location_id': self.stock_subloc2})

    def test_update_quant_with_forbidden_field_02(self):
        """
        Test that updating the package from the quant raise an error
        but if the package is unpacked, the quant can be updated.
        """
        package = self.env['stock.quant.package'].create({
            'name': 'Package',
        })
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, package_id=package)
        quant = self.product.stock_quant_ids
        self.assertEqual(len(self.product.stock_quant_ids), 1)
        with self.assertRaises(UserError):
            quant.with_context(inventory_mode=True).write({'package_id': False})
        package.with_context(inventory_mode=True).unpack()
        self.assertFalse(quant.exists())
        self.assertFalse(self.product.stock_quant_ids.package_id)

    def test_relocate(self):
        """ Test the relocation wizard. """
        def _get_relocate_wizard(quant_ids):
            return Form.from_action(self.env, quant_ids.action_stock_quant_relocate())

        self.env['stock.quant.package'].search([]).unlink()
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_tracking_lot').id)]})
        package_01 = self.env['stock.quant.package'].create({})
        package_02 = self.env['stock.quant.package'].create({})
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 10, package_id=package_01)
        quant_a = self.env['stock.quant'].search([('product_id', '=', self.product.id)])

        # testing assigning a package to a quant
        relocate_wizard = _get_relocate_wizard(quant_a)
        relocate_wizard.dest_package_id = package_02
        action = relocate_wizard.save().action_relocate_quants()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'stock.quant')

        new_quant_a = self.env['stock.quant'].search([('product_id', '=', self.product.id), ('quantity', '=', 10)])
        self.assertEqual(new_quant_a.package_id, package_02)

        # testing moving a packed quant to a new location
        relocate_wizard = _get_relocate_wizard(new_quant_a)
        self.assertEqual(relocate_wizard.is_partial_package, False)
        relocate_wizard.dest_location_id = self.stock_subloc2
        relocate_wizard.save().action_relocate_quants()
        new_quant_a_bis = self.env['stock.quant'].search([('product_id', '=', self.product.id), ('quantity', '=', 10)])
        self.assertEqual(new_quant_a_bis.location_id, self.stock_subloc2)
        self.assertEqual(new_quant_a_bis.package_id, package_02)

        # testing moving multiple packed quants to a new location with incomplete package
        product_b = self.env['product.product'].create({
            'name': 'product B',
            'is_storable': True
        })
        self.env['stock.quant']._update_available_quantity(product_b, self.stock_location, 10, package_id=package_01)
        product_c = self.env['product.product'].create({
            'name': 'product C',
            'is_storable': True
        })
        self.env['stock.quant']._update_available_quantity(product_c, self.stock_location, 10, package_id=package_01)

        quants_ab = self.env['stock.quant'].search([('product_id', 'in', (self.product.id, product_b.id)), ('quantity', '=', 10)])
        relocate_wizard = _get_relocate_wizard(quants_ab)
        self.assertEqual(relocate_wizard.is_partial_package, True)

        relocate_wizard.dest_location_id = self.stock_subloc3
        relocate_wizard.save().action_relocate_quants()
        new_quants_abc = self.env['stock.quant'].search([('product_id', 'in', (self.product.id, product_b.id, product_c.id)), ('quantity', '=', 10)], order='product_id')
        self.assertRecordValues(new_quants_abc, [
            {'product_id': self.product.id, 'location_id': self.stock_subloc3.id, 'package_id': package_02.id},
            {'product_id': product_b.id, 'location_id': self.stock_subloc3.id, 'package_id': False},
            {'product_id': product_c.id, 'location_id': self.stock_location.id, 'package_id': package_01.id},
        ])

        ### CURRENT STATE
            # COMPANY A
            #     product A (self.product): stock_subloc3, package_02
            #     product B: stock_subloc3, no package
            #     product C: stock_location, package_01

        ### testing blocks on relocating quants from different companies
        package_03 = self.env['stock.quant.package'].create({})
        package_04 = self.env['stock.quant.package'].create({})
        company_B = self.env['res.company'].create({
            'name': 'company B',
            'currency_id': self.env.ref('base.USD').id
        })
        location_company_B = self.env['stock.location'].create({
            'name': 'stock location company B',
            'usage': 'internal',
            'company_id': company_B.id
        })
        product_a_company_B = self.env['product.product'].create({
            'name': 'product A company B',
            'is_storable': True,
            'company_id': company_B.id
        })
        product_b_company_B = self.env['product.product'].create({
            'name': 'product b company B',
            'is_storable': True,
            'company_id': company_B.id
        })
        self.env['stock.quant']._update_available_quantity(product_a_company_B, location_company_B, 10, package_id=package_03)
        self.env['stock.quant']._update_available_quantity(product_b_company_B, location_company_B, 10)

        # testing the available packs from company B
        quant_b_B = self.env['stock.quant'].search([('product_id', '=', product_b_company_B.id), ('quantity', '=', 10)])
        relocate_wizard = _get_relocate_wizard(quant_b_B)
        self.assertEqual(relocate_wizard.dest_package_id.search(literal_eval(relocate_wizard.dest_package_id_domain)), package_03+package_04)

        # testing the available packs from company A with multiple quants
        quants_ab_A = self.env['stock.quant'].search([('product_id', 'in', (self.product.id, product_b.id)), ('quantity', '=', 10)])
        relocate_wizard = _get_relocate_wizard(quants_ab_A)
        self.assertEqual(relocate_wizard.dest_package_id.search(literal_eval(relocate_wizard.dest_package_id_domain)), package_02+package_04)

        # testing the recomputation of available packages
        relocate_wizard.dest_location_id = self.stock_location
        self.assertEqual(relocate_wizard.dest_package_id.search(literal_eval(relocate_wizard.dest_package_id_domain)), package_01+package_04)

        # testing calling the wizard with quants from multiple companies
        quants_bab_AB = quant_b_B + quants_ab_A
        with self.assertRaises(UserError):
            _get_relocate_wizard(quants_bab_AB)

    def test_inventory_adjustment_package(self):
        """ With the changes implemented in _get_inventory_move_values(), we want to make sure that it correctly
        writes the package and destination package for inventory adjustments in _apply_inventory(). """

        dummy_product = self.env['product.product'].create({'name': 'dummy product', 'is_storable': True})
        dummy_package = self.env['stock.quant.package'].create({'name': 'dummy package'})
        dummy_quant = self.env['stock.quant'].create({
            'product_id': dummy_product.id,
            'location_id': self.stock_location.id,
            'package_id': dummy_package.id,
            'inventory_quantity': 42
        })
        dummy_quant.action_apply_inventory()

        creation_move_line = self.env['stock.move.line'].search([('product_id', '=', dummy_product.id)])
        self.assertEqual(creation_move_line.package_id.id, False, "There should be no origin package")
        self.assertEqual(creation_move_line.result_package_id.id, dummy_package.id, "The destination package should be the dummy package")
        self.assertEqual(creation_move_line.location_dest_id.id, self.stock_location.id, "The destination location should be the stock location")

        dummy_quant.inventory_quantity = 0
        dummy_quant.action_apply_inventory()

        destruction_move_line = self.env['stock.move.line'].search([('product_id', '=', dummy_product.id), ('id', '!=', creation_move_line.id)])
        self.assertEqual(destruction_move_line.package_id.id, dummy_package.id, "The origin package should be the dummy package")
        self.assertEqual(destruction_move_line.result_package_id.id, False, "The destination package should be False")
        self.assertEqual(destruction_move_line.location_id.id, self.stock_location.id, "The origin location should be the stock location")
        self.assertEqual(destruction_move_line.location_dest_id.id, creation_move_line.location_id.id)
        self.assertEqual(dummy_quant.quantity, 0)

    def test_quant_gs1_barcode(self):
        """ Checks quant's methods to generate barcode works as expected and don't
        generate barcodes longer than the given limit and use the given separator.
        """
        # Initial config.
        self.env['ir.config_parameter'].set_param('stock.agg_barcode_max_length', 400)
        self.env['ir.config_parameter'].set_param('stock.barcode_separator', ';')
        # Create some products with a valid EAN-13 and LN/SN for tracked ones.
        product_ean13 = self.env['product.product'].create({
            'name': 'Product Test EAN13',
            'is_storable': True,
            'barcode': '0100011101014',
        })
        product_serial_ean13 = self.env['product.product'].create({
            'name': 'Product Test EAN13 - Tracked by SN',
            'is_storable': True,
            'barcode': '0200022202028',
            'tracking': 'serial',
        })
        product_lot_ean13 = self.env['product.product'].create({
            'name': 'Product Test EAN13 - Tracked by Lots',
            'is_storable': True,
            'barcode': '0300033303032',
            'tracking': 'lot',
        })

        serial_numbers = self.env['stock.lot'].create([{
            'product_id': product_serial_ean13.id,
            'name': f'tsn-00{i}',
        } for i in range(8)])

        lot_numbers = self.env['stock.lot'].create([{
            'product_id': product_lot_ean13.id,
            'name': f'lot-00{i}',
        } for i in range(2)])

        # Add some quants for those products.
        common_serial_vals = {
            'product_id': product_serial_ean13.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 1,
        }
        serial_vals = [{
            **common_serial_vals,
            'lot_id': serial_numbers[i].id,
        } for i in range(8)]
        quants = self.env['stock.quant'].create(serial_vals + [{
            'product_id': product_ean13.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 123,
        }, {
            'product_id': product_lot_ean13.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 15,
            'lot_id': lot_numbers[0].id,
        }, {
            'product_id': product_lot_ean13.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 25,
            'lot_id': lot_numbers[1].id,
        }])
        quants.action_apply_inventory()

        quants_product_ean13 = quants.filtered(lambda q: q.product_id == product_ean13)
        quants_product_serial_ean13 = quants.filtered(lambda q: q.product_id == product_serial_ean13)
        quants_product_lot_ean13 = quants.filtered(lambda q: q.product_id == product_lot_ean13)

        # First, check each individual barcodes.
        self.assertEqual(quants_product_ean13._get_gs1_barcode(), '01001000111010143000000123')
        self.assertEqual(quants_product_serial_ean13[3]._get_gs1_barcode(), '010020002220202821tsn-003')
        self.assertEqual(quants_product_lot_ean13[1]._get_gs1_barcode(), '0100300033303032300000002510lot-001')

        # Then, check the aggregate barcode.
        aggregate_barcodes = quants.sorted(lambda q: q.product_id.id).get_aggregate_barcodes()
        self.assertEqual(len(aggregate_barcodes), 1)
        self.assertEqual(
            aggregate_barcodes[0],
            "01001000111010143000000123;010020002220202821tsn-000;010020002220202821tsn-001;"
            "010020002220202821tsn-002;010020002220202821tsn-003;010020002220202821tsn-004;"
            "010020002220202821tsn-005;010020002220202821tsn-006;010020002220202821tsn-007;"
            "0100300033303032300000001510lot-000;0100300033303032300000002510lot-001\t"
        )

        # Use another separator and set a lower aggregate barcode's max length.
        self.env['ir.config_parameter'].set_param('stock.barcode_separator', '|')
        self.env['ir.config_parameter'].set_param('stock.agg_barcode_max_length', 160)
        aggregate_barcodes = quants.sorted(lambda q: q.product_id.id).get_aggregate_barcodes()
        # Check we have now two aggregate barcodes (306 char but limit at 160).
        self.assertEqual(len(aggregate_barcodes), 2)
        for aggregate_barcode in aggregate_barcodes:
            self.assertTrue(
                len(aggregate_barcode) <= 160,
                "Every aggregate barcode should be shorter than the barcode max size limit")
        self.assertEqual(
            aggregate_barcodes[0],
            "01001000111010143000000123|010020002220202821tsn-000|010020002220202821tsn-001|"
            "010020002220202821tsn-002|010020002220202821tsn-003|010020002220202821tsn-004\t"
        )
        self.assertEqual(
            aggregate_barcodes[1],
            "010020002220202821tsn-005|010020002220202821tsn-006|010020002220202821tsn-007|"
            "0100300033303032300000001510lot-000|0100300033303032300000002510lot-001\t"
        )

    def test_quant_aggregate_barcode(self):
        """ Checks quant's methods to generate barcode works for tracked products
        regardless the product's barcode is a valid EAN or not.
        """
        # Initial config.
        self.env['ir.config_parameter'].set_param('stock.agg_barcode_max_length', 400)
        self.env['ir.config_parameter'].set_param('stock.barcode_separator', ';')
        # Creates some product with not GS1 compliant barcodes.
        product = self.env['product.product'].create({
            'name': "Product Test",
            'is_storable': True,
            'barcode': 'PRODUCT-TEST',
        })
        product_serial = self.env['product.product'].create({
            'name': "Product Test - Tracked by SN",
            'is_storable': True,
            'barcode': 'PRODUCT-SN',
            'tracking': 'serial',
        })
        product_lot = self.env['product.product'].create({
            'name': "Product Test - Tracked by Lots",
            'is_storable': True,
            'barcode': 'PRODUCT-LN',
            'tracking': 'lot',
        })
        # Creates some lot/serial numbers.
        serial_numbers = self.env['stock.lot'].create([{
            'product_id': product_serial.id,
            'name': f'tsn-00{i}',
        } for i in range(8)])

        lot_numbers = self.env['stock.lot'].create([{
            'product_id': product_lot.id,
            'name': f'lot-00{i}',
        } for i in range(2)])

        # Add some quants for those products.
        common_serial_vals = {
            'product_id': product_serial.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 1,
        }
        serial_vals = [{
            **common_serial_vals,
            'lot_id': serial_numbers[i].id,
        } for i in range(8)]
        quants = self.env['stock.quant'].create(serial_vals + [{
            'product_id': product.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 123,
        }, {
            'product_id': product_lot.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 15,
            'lot_id': lot_numbers[0].id,
        }, {
            'product_id': product_lot.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 25,
            'lot_id': lot_numbers[1].id,
        }])
        quants.action_apply_inventory()

        quants_product = quants.filtered(lambda q: q.product_id == product)
        quants_product_serial = quants.filtered(lambda q: q.product_id == product_serial)
        quants_product_lot = quants.filtered(lambda q: q.product_id == product_lot)

        # Check each individual barcodes.
        self.assertEqual(quants_product._get_gs1_barcode(), '')
        self.assertEqual(quants_product_serial[3]._get_gs1_barcode(), '21tsn-003')
        self.assertEqual(quants_product_lot[1]._get_gs1_barcode(), '300000002510lot-001')

        # Check the aggregate barcode.
        aggregate_barcodes = quants.sorted(lambda q: q.product_id.id).get_aggregate_barcodes()
        self.assertEqual(len(aggregate_barcodes), 1)
        self.assertEqual(
            aggregate_barcodes[0],
            "PRODUCT-TEST;PRODUCT-SN;21tsn-000;21tsn-001;21tsn-002;21tsn-003;21tsn-004;"
            "21tsn-005;21tsn-006;21tsn-007;PRODUCT-LN;300000001510lot-000;300000002510lot-001\t")

    def test_unpack_and_quants_history(self):
        """
        Test that after unpacking the quant history is preserved
        """
        product = self.env['product.product'].create({
            'name': 'Product',
            'is_storable': True,
            'tracking': 'lot',
        })
        lot_a = self.env['stock.lot'].create({
            'name': 'A',
            'product_id': product.id,
            'product_qty': 5,
        })
        package = self.env['stock.quant.package'].create({
            'name': 'Super Package',
        })
        stock_location = self.stock_location
        dst_location = self.stock_subloc2
        picking_type = self.env.ref('stock.picking_type_internal')

        self.env['stock.quant']._update_available_quantity(product, stock_location, 5.0, lot_id=lot_a, package_id=package)

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': dst_location.id,
            'location_dest_id': stock_location.id,
            'move_ids': [(0, 0, {
                'name': 'In 5 x %s' % product.name,
                'product_id': product.id,
                'location_id': stock_location.id,
                'location_dest_id': dst_location.id,
                'product_uom_qty': 5,
                'product_uom': product.uom_id.id,
            })],
        })
        picking.action_confirm()

        picking.move_ids.move_line_ids.write({
            'quantity': 5,
            'lot_id': lot_a.id,
            'package_id': package.id,
            'result_package_id': package.id,
        })
        picking.button_validate()
        package.unpack()

        quant = self.env['stock.quant'].search([
            ('product_id', '=', product.id),
            ('location_id', '=', dst_location.id),
        ])
        action = quant.action_view_stock_moves()
        history = self.env['stock.move.line'].search(action['domain'])
        self.assertTrue(history)

    def test_reserve_fractional_qty(self):
        lot1 = self.env['stock.lot'].create({'name': 'lot1', 'product_id': self.product_serial.id})
        lot2 = self.env['stock.lot'].create({'name': 'lot2', 'product_id': self.product_serial.id})
        for lot in (lot1, lot2):
            self.env['stock.quant']._update_available_quantity(
                product_id=self.product_serial,
                location_id=self.stock_location,
                quantity=1,
                lot_id=lot,
            )
        move = self.env['stock.move'].create({
            'name': 'test_reserve_small_qty',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_subloc2.id,
            'product_id': self.product_serial.id,
            'product_uom_qty': 1.1,
        })
        move._action_confirm()
        move._action_assign()
        self.assertFalse(move.quantity)

    def test_lot_of_product_different_from_quant(self):
        """
        Test that a lot cannot be used in a quant if the product is different.
        """
        product_lot_2 = self.env['product.product'].create({
            'name': 'Product',
            'is_storable': True,
            'tracking': 'lot',
        })
        lot_a = self.env['stock.lot'].create({
            'name': 'A',
            'product_id': product_lot_2.id,
            'product_qty': 5,
        })
        with self.assertRaises(ValidationError):
            self.env['stock.quant'].create({
                'product_id': self.product_lot.id,
                'location_id': self.stock_location.id,
                'quantity': 20.0,
                'lot_id': lot_a.id,
            })

    def test_set_on_hand_quantity_tracked_product(self):
        """
        Checks that you can update the on hand quantity of a tracked product
        on a quant without a set lot.
        """
        quant_without_lot = self.env['stock.quant'].create({
            'product_id': self.product_lot.id,
            'location_id': self.stock_location.id,
            'lot_id': False,
        })
        quant_without_lot.with_context({'inventory_mode': True}).inventory_quantity_auto_apply = 10.0
        self.assertRecordValues(quant_without_lot, [{
            'product_id': self.product_lot.id,
            'quantity': 10.0,
            'lot_id': False,
        }])


class StockQuantRemovalStrategy(TransactionCase):
    def setUp(self):
        super().setUp()
        self.least_package_strategy = self.env['product.removal'].search(
            [('method', '=', 'least_packages')])
        self.product = self.env['product.product'].create({
            'name': 'Product',
            'is_storable': True,
        })
        self.product.categ_id.removal_strategy_id = self.least_package_strategy.id
        self.stock_location = self.env['stock.location'].create({
            'name': 'stock_location',
            'usage': 'internal',
        })

    def _generate_data(self, packages_data):
        move = self.env['stock.move'].create({
            'name': 'Test Least Package',
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'location_id': self.ref('stock.stock_location_suppliers'),
            'location_dest_id': self.stock_location.id,
        })
        move._action_confirm()

        ml_vals_list = []
        ml_common_vals = {
            'move_id': move.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'location_id': self.ref('stock.stock_location_suppliers'),
            'location_dest_id': self.stock_location.id,
        }

        packages = self.env['stock.quant.package'].create(
            [{}] * sum(p[1] for p in packages_data if p[0]))
        for package_size, number_of_packages in packages_data:
            if not package_size:
                ml_vals_list.append(dict(**ml_common_vals, **{
                    'quantity': number_of_packages,
                }))
                continue
            for dummy in range(number_of_packages):
                package = packages[0]
                packages = packages[1:]
                ml_vals_list.append(dict(**ml_common_vals, **{
                    'quantity': package_size,
                    'result_package_id': package.id,
                }))
        self.env['stock.move.line'].create(ml_vals_list)
        move.picked = True
        move._action_done()

    def test_least_package_removal_strategy_priority_to_package(self):
        """
        Tests the least package removal strategy in a use case where only one package needs to be selected.
        It should only return the quantity of a single size 1000 package.
        """
        packages_data = [
            (False, 2000),
            (5, 10),
            (50, 10),
            (1000, 2),
        ]
        self._generate_data(packages_data)

        # Out 1000 should selecte a package with 1000 units inside
        move = self.env['stock.move'].create({
            'name': 'Test Least Package',
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'product_uom_qty': 1000,
        })
        move._action_confirm()
        move._action_assign()
        self.assertEqual(len(move.move_line_ids), 1, 'Only one pack could be use')
        self.assertTrue(
            move.move_line_ids.package_id,
            'A package should be selected, priority to package even if there is enough quantity without package'
        )

    def test_least_package_removal_strategy_simple_usecase(self):
        """
         Tests the least package removal strategy in a simple "typical" use case.
         It should return a minimal exact matching for the requested quantity.
        """
        packages_data = [
            (5, 10),
            (50, 10),
            (1000, 2),
        ]
        self._generate_data(packages_data)

        # Out 1000 should select a package with 1000 units inside
        move = self.env['stock.move'].create({
            'name': 'Test Least Package',
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'product_uom_qty': 1280,
        })
        move._action_confirm()
        move._action_assign()
        self.assertEqual(len(move.move_line_ids), 12)
        self.assertRecordValues(
            move.move_line_ids,
            [{'quantity_product_uom': 1000}] +
            [{'quantity_product_uom': 50}] * 5 +
            [{'quantity_product_uom': 5}] * 6
        )

    def test_least_package_removal_strategy_not_possible(self):
        """
        Tests the least package removal strategy in the case where an exact matching
        of packages is not possible for the requested amount.
        It should return the best leaf from the A* search.
        """
        packages_data = [
            (False, 2),
            (5, 2),
            (10, 5),
        ]
        self._generate_data(packages_data)

        move = self.env['stock.move'].create({
            'name': 'Test Least Package',
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'product_uom_qty': 13,
        })
        move._action_confirm()
        move._action_assign()
        self.assertEqual(len(move.move_line_ids), 2)
        self.assertRecordValues(
            move.move_line_ids,
            [{'quantity_product_uom': 10}] + [{'quantity_product_uom': 3}]
        )
        # Make sure it selects the smallest possible package as best leaf.
        self.assertEqual(
            move.move_line_ids[1].package_id.quant_ids.quantity,
            5
        )

    def test_least_package_removal_strategy_not_enough(self):
        """
        Tests the least package removal strategy in the case where not enough quantity
        is available to fill the requested amount.
        It should just return all the quantities in the domain.
        """
        packages_data = [
            (False, 2),
            (5, 2),
            (10, 5),
        ]
        self._generate_data(packages_data)

        move = self.env['stock.move'].create({
            'name': 'Test Least Package',
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'product_uom_qty': 90,
        })
        move._action_confirm()
        move._action_assign()
        self.assertEqual(len(move.move_line_ids), 8)
        self.assertRecordValues(
            move.move_line_ids,
            [{'quantity_product_uom': 2}] +
            [{'quantity_product_uom': 10}] * 5 +
            [{'quantity_product_uom': 5}] * 2
        )

    def test_clean_quant_after_package_move(self):
        """
        A product is at WH/Stock in a package PK. We deliver PK. The user should
        not find any quant at WH/Stock with PK anymore.
        """
        package = self.env['stock.quant.package'].create({})
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, package_id=package)

        move = self.env['stock.move'].create({
            'name': 'OUT 1 product',
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'product_uom': self.product.uom_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
        })
        move._action_confirm()
        move._action_assign()
        move.move_line_ids.write({
            'result_package_id': package.id,
            'quantity': 1,
        })
        move.picked = True
        move._action_done()

        self.assertFalse(self.env['stock.quant'].search_count([
            ('product_id', '=', self.product.id),
            ('package_id', '=', package.id),
            ('location_id', '=', self.stock_location.id),
        ]))
