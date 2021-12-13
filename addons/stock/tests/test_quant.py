# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import closing
from datetime import datetime, timedelta

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import ValidationError
from odoo.tests.common import SavepointCase
from odoo.exceptions import AccessError, RedirectWarning, UserError


class StockQuant(SavepointCase):
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
        lot1 = self.env['stock.production.lot'].create({
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
        with self.assertRaises(UserError):
            self.env['stock.quant']._update_reserved_quantity(self.product, self.stock_location, 10.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)

    def test_increase_reserved_quantity_5(self):
        """ Decrease the available quantity when no quant are in a location.
        """
        with self.assertRaises(UserError):
            self.env['stock.quant']._update_reserved_quantity(self.product, self.stock_location, 1.0)
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
        with self.assertRaises(UserError):
            self.env['stock.quant']._update_reserved_quantity(self.product, self.stock_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        with self.assertRaises(RedirectWarning):
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
        lot1 = self.env['stock.production.lot'].create({
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

        with self.assertRaises(RedirectWarning):
            self.env['stock.quant']._update_reserved_quantity(self.product_serial, self.stock_location, -1.0, strict=True)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, strict=True), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot1), 2.0)

    def test_access_rights_1(self):
        """ Directly update the quant with a user with or without stock access rights sould raise
        an AccessError.
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
        with self.assertRaises(AccessError):
            quant.with_user(self.demo_user).unlink()

        self.env = self.env(user=self.stock_user)
        with self.assertRaises(AccessError):
            self.env['stock.quant'].create({
                'product_id': self.product.id,
                'location_id': self.stock_location.id,
                'quantity': 1.0,
            })
        with self.assertRaises(AccessError):
            quant.with_user(self.demo_user).write({'quantity': 2.0})
        with self.assertRaises(AccessError):
            quant.with_user(self.demo_user).unlink()

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
        lot1 = self.env['stock.production.lot'].create({
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
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
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
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
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

    def test_in_date_4b(self):
        """ Check for LIFO and max with/without in_date that it handles the LIFO NULLS LAST well
        """
        stock_location1 = self.env['stock.location'].create({
            'name': 'Shelf 1',
            'location_id': self.stock_location.id
        })
        stock_location2 = self.env['stock.location'].create({
            'name': 'Shelf 2',
            'location_id': self.stock_location.id
        })
        lifo_strategy = self.env['product.removal'].search([('method', '=', 'lifo')])
        self.stock_location.removal_strategy_id = lifo_strategy

        self.env['stock.quant'].create({
            'product_id': self.product_serial.id,
            'location_id': stock_location1.id,
            'quantity': 1.0,
        })

        in_date_location2 = datetime.now()
        self.env['stock.quant']._update_available_quantity(self.product_serial, stock_location2, 1.0, in_date=in_date_location2)

        quants = self.env['stock.quant']._update_reserved_quantity(self.product_serial, self.stock_location, 1)

        # Removal strategy is LIFO, so the one with date is the most recent one and should be selected
        self.assertEqual(quants[0][0].location_id.id, stock_location2.id)

    def test_in_date_5(self):
        """ Receive the same lot at different times, once they're in the same location, the quants
        are merged and only the earliest incoming date is kept.
        """
        lot1 = self.env['stock.production.lot'].create({
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
