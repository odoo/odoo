# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from contextlib import closing
from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
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
            'type': 'product',
        })
        cls.product_lot = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'tracking': 'lot',
        })
        cls.product_consu = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'consu',
        })
        cls.product_serial = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
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
            'company_id': self.env.company.id,
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
            'type': 'product',
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

    def test_increase_decrease_reserved_quantity_1(self):
        """ Decrease then increase reserved quantity when no quant are in a location.
        """
        self.env['stock.quant']._update_reserved_quantity(self.product, self.stock_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        with self.assertRaises(UserError):
            self.env['stock.quant']._update_reserved_quantity(self.product, self.stock_location, -1.0, strict=True)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)

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
            'company_id': self.env.company.id,
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

        with self.assertRaises(UserError):
            self.env['stock.quant']._update_reserved_quantity(self.product_serial, self.stock_location, -1.0, strict=True)

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

    def test_in_date_1(self):
        """ Check that no incoming date is set when updating the quantity of an untracked quant.
        """
        quantity, in_date = self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0)
        self.assertEqual(quantity, 1)
        self.assertNotEqual(in_date, None)

    def test_in_date_1b(self):
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 1.0,
        })
        quantity, in_date = self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 2.0)
        self.assertEqual(quantity, 3)
        self.assertNotEqual(in_date, None)

    def test_in_date_2(self):
        """ Check that an incoming date is correctly set when updating the quantity of a tracked
        quant.
        """
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        quantity, in_date = self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0, lot_id=lot1)
        self.assertEqual(quantity, 1)
        self.assertNotEqual(in_date, None)

    def test_in_date_3(self):
        """ Check that the FIFO strategies correctly applies when you have multiple lot received
        at different times for a tracked product.
        """
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.lot'].create({
            'name': 'lot2',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        in_date_lot1 = datetime.now()
        in_date_lot2 = datetime.now() - timedelta(days=5)
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0, lot_id=lot1, in_date=in_date_lot1)
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0, lot_id=lot2, in_date=in_date_lot2)

        quants = self.env['stock.quant']._update_reserved_quantity(self.product_serial, self.stock_location, 1)

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
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.lot'].create({
            'name': 'lot2',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        in_date_lot1 = datetime.now()
        in_date_lot2 = datetime.now() - timedelta(days=5)
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0, lot_id=lot1, in_date=in_date_lot1)
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0, lot_id=lot2, in_date=in_date_lot2)

        quants = self.env['stock.quant']._update_reserved_quantity(self.product_serial, self.stock_location, 1)

        # Removal strategy is LIFO, so lot1 should be received as it was received later.
        self.assertEqual(quants[0][0].lot_id.id, lot1.id)

    def test_in_date_5(self):
        """ Receive the same lot at different times, once they're in the same location, the quants
        are merged and only the earliest incoming date is kept.
        """
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.product_lot.id,
            'company_id': self.env.company.id,
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
        closest_strategy = self.env['product.removal'].search([('method', '=', 'closest')])
        self.stock_location.removal_strategy_id = closest_strategy
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.lot'].create({
            'name': 'lot2',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        in_date = datetime.now()
        # Add a product from lot1 in stock_location/subloc2
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_subloc2, 1.0, lot_id=lot1, in_date=in_date)
        # Add a product from lot2 in stock_location/subloc3
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_subloc3, 1.0, lot_id=lot2, in_date=in_date)
        # Require one unit of the product
        quants = self.env['stock.quant']._update_reserved_quantity(self.product_serial, self.stock_location, 1)

        # Default removal strategy is 'Closest location', so lot1 should be received as it was put in a closer location. (stock_location/subloc2 < stock_location/subloc3)
        self.assertEqual(quants[0][0].lot_id.id, lot1.id)

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
        quants = self.env['stock.quant']._update_reserved_quantity(self.product, self.stock_location, 3)

        # The 2 in stock_location/subloc2 should be taken first, as the location name is smaller alphabetically
        self.assertEqual(quants[0][0].reserved_quantity, 2)
        # The last one should then be taken in stock_location/subloc3 since the first location doesn't have enough products
        self.assertEqual(quants[1][0].reserved_quantity, 1)

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
        move.quantity_done = 1
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
            move.quantity_done = 1
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
        move.quantity_done = 1
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
        })
        picking.action_confirm()

        package = self.env['stock.quant.package'].create({
            'name': 'Super Package',
        })
        picking.move_ids.move_line_ids.write({
            'qty_done': 10,
            'result_package_id': package.id,
        })
        picking.button_validate()

        package.unpack()

        quant = self.env['stock.quant'].search([('product_id', '=', self.product.id), ('on_hand', '=', True)])
        self.assertEqual(len(quant), 1)
        # The quants merging is processed thanks to a SQL query (see StockQuant._merge_quants).
        # At that point, the ORM is not aware of the new value. So we need to invalidate the
        # cache to ensure that the value will be the newest
        quant.invalidate_recordset(['quantity'])
        self.assertEqual(quant.quantity, 11)

class StockQuantRemovalStrategy(TransactionCase):
    def setUp(self):
        super().setUp()
        self.least_package_strategy = self.env['product.removal'].search(
            [('method', '=', 'least_packages')])
        self.product = self.env['product.product'].create({
            'name': 'Product',
            'type': 'product',
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
                    'qty_done': number_of_packages,
                }))
                continue
            for dummy in range(number_of_packages):
                package = packages[0]
                packages = packages[1:]
                ml_vals_list.append(dict(**ml_common_vals, **{
                    'qty_done': package_size,
                    'result_package_id': package.id,
                }))
        self.env['stock.move.line'].create(ml_vals_list)
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
            [{'reserved_qty': 1000}] +
            [{'reserved_qty': 50}] * 5 +
            [{'reserved_qty': 5}] * 6
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
            [{'reserved_qty': 10}] + [{'reserved_qty': 3}]
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
            [{'reserved_qty': 2}] +
            [{'reserved_qty': 10}] * 5 +
            [{'reserved_qty': 5}] * 2
        )

    def test_quant_reserve(self):
        """ Tests the reserve stock wizard which allows to choose a specific quant to reserve from
            also checks if editing the reserved_uom_qty on stock.move.line updates the quants
        """
        customer_location = self.env.ref('stock.stock_location_customers')
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'quantity': 2,
            'location_id': self.stock_location.id
        })
        move_id = self.env['stock.move'].create({
            'name': 'move out',
            'location_id': self.stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 2.0,
        })
        move_id._action_confirm()
        move_id._action_assign()
        self.assertEqual(move_id.state, 'assigned')
        self.assertEqual(len(move_id.move_line_ids), 1)
        self.assertEqual(move_id.move_line_ids.reserved_uom_qty, 2)
        # available should be 0
        available_qty = self.env['stock.quant']._get_available_quantity(self.product, self.stock_location)
        self.assertEqual(available_qty, 0)
        # unreserve, qty available should be 2 and move state back to confirmed
        move_id.move_line_ids.reserved_uom_qty = 0
        available_qty = self.env['stock.quant']._get_available_quantity(self.product, self.stock_location)
        self.assertEqual(available_qty, 2)
        self.assertEqual(move_id.state, 'confirmed')
        # reserve qty again, checks to be able to reserve from confirmed state, and only reserve what's available
        move_id.move_line_ids.reserved_uom_qty = 4
        self.assertEqual(move_id.state, 'assigned')
        self.assertEqual(move_id.move_line_ids.reserved_uom_qty, 2)
        # unreserve and try to reserve from wizard
        move_id.move_line_ids.unlink()
        wiz_action = self.env['stock.move.line'].with_context(default_move_id=move_id.id).action_open_reserve_stock()
        wiz = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({})
        self.assertEqual(wiz.move_id.id, move_id.id)
        self.assertEqual(wiz.demand_qty, move_id.product_qty)
        self.assertEqual(len(wiz.quant_line_ids), 1)
        wiz.quant_line_ids.qty_to_reserve = 4
        with self.assertRaises(UserError):
            wiz.reserve_stock()
        wiz.quant_line_ids.qty_to_reserve = 2
        wiz.reserve_stock()
        self.assertEqual(len(move_id.move_line_ids), 1)
        self.assertEqual(move_id.state, 'assigned')
        self.assertEqual(move_id.move_line_ids.reserved_uom_qty, 2)
        move_id._set_quantities_to_reservation()
        move_id._action_done()
        self.assertEqual(move_id.state, 'done')
