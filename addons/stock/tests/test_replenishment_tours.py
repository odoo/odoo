# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, timedelta

from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestReplenishmentView(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Tours are run as 'admin'
        cls.env.ref('base.user_admin').group_ids += cls.env.ref('stock.group_stock_multi_locations')

        cls.spoon = cls.env['product.template'].create({
            'name': 'Spoon',
            'is_storable': True,
        })
        cls.fork, cls.knife = cls.env['product.product'].create([{
            'name': name,
            'is_storable': True,
        } for name in ('Fork', 'Knife')])

        material = cls.env['product.attribute'].create({'name': 'Material'})
        cls.env['product.template.attribute.line'].create({
            'attribute_id':  material.id,
            'value_ids': [Command.create({'name': name, 'attribute_id': material.id})
                          for name in ('Steel', 'Wood', 'Plastic')],
            'product_tmpl_id': cls.spoon.id,
        })
        cls.steel_spoon, cls.wooden_spoon, cls.plastic_spoon = cls.spoon.product_variant_ids

        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.shelfA, cls.shelfB, cls.shelfC = cls.env['stock.location'].create([{
            'name': 'Shelf %s' % name,
            'usage': 'internal',
            'location_id': cls.stock_location.id,
        } for name in ('A', 'B', 'C')])

        cls.replenishment_view_url = '/odoo/replenishment'

    def _get_product_url(self, product_id):
        return '/odoo/product.template/%s' % product_id

    def _make_order(self, product, location, inventory_qty, min_qty, max_qty, qty_to_order):
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product.id,
            'location_id': location.id,
            'inventory_quantity': inventory_qty,
        }).action_apply_inventory()
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
                    'name': '%s rule for %s' % (product.display_name, location.display_name),
                    'product_id': product.id,
                    'location_id': location.id,
                    'product_min_qty': min_qty,
                    'product_max_qty': max_qty,
                    'trigger': 'manual',
                    'qty_to_order': qty_to_order,
                })
        return {'product': product,
                'location': location,
                'orderpoint': orderpoint}

    def _check_replenishment_move(self, order, qty):
        return bool(self.env['stock.move'].search_count(
            [('product_id', '=', order['product'].id),
             ('location_dest_id', '=', order['location'].id),
             ('product_qty', '=', qty),
             ]))

    def test_orderpoint_list_view_buttons(self):
        """
        Check that the 'Snooze', 'Order' and 'Order to Max' buttons work as
        intended in the Replenishment view. Checks products and their variants
        for both single and batch operations.
        """

        # Order
        spoon0 = self._make_order(self.wooden_spoon, self.shelfA, 10, 12, 15,  3)
        # Order to Max
        spoon1 = self._make_order(self.wooden_spoon, self.shelfB, 20, 24, 30,  6)
        # Order
        spoon2 = self._make_order(self.steel_spoon,  self.shelfA, 30, 36, 45,  9)
        spoon3 = self._make_order(self.steel_spoon,  self.shelfB, 40, 48, 60, 12)
        # Order to Max
        fork0 =  self._make_order(self.fork,         self.shelfA, 50, 60, 75, 15)
        fork1 =  self._make_order(self.fork,         self.shelfB, 60, 72, 90, 18)
        # Snooze
        knife0 = self._make_order(self.knife,        self.shelfA,  5, 10, 15,  2)
        knife1 = self._make_order(self.knife,        self.shelfB,  5, 10, 15,  2)
        knife2 = self._make_order(self.knife,        self.shelfC,  5, 10, 15,  2)

        self.start_tour(self.replenishment_view_url, 'test_orderpoint_list_view_buttons', login='admin', step_delay=200)
        self.env['procurement.group'].run_scheduler()

        # Order
        self.assertTrue(self._check_replenishment_move(spoon0, 3))
        # Order to Max
        self.assertTrue(self._check_replenishment_move(spoon1, 10))
        # Snooze, 1 week
        self.assertEqual(knife0['orderpoint'].snoozed_until, date.today() + timedelta(weeks=1))

        # Order in batch
        self.assertTrue(self._check_replenishment_move(spoon2, 9))
        self.assertTrue(self._check_replenishment_move(fork0, 15))
        # Order to Max in batch
        self.assertTrue(self._check_replenishment_move(spoon3, 20))
        self.assertTrue(self._check_replenishment_move(fork1, 30))
        # Snooze in batch, 1 day
        self.assertEqual(knife1['orderpoint'].snoozed_until, date.today() + timedelta(days=1))
        self.assertEqual(knife2['orderpoint'].snoozed_until, date.today() + timedelta(days=1))

    def test_orderpoint_product_view_buttons(self):
        """
        Check that the 'Snooze', 'Order' and 'Order to Max' buttons work as
        intended in both the product Reordering Rules view. Checks products
        and their variants for both single and batch operations.
        """

        # Order
        spoon0 = self._make_order(self.wooden_spoon,   self.shelfA, 10, 12, 15,  3)
        # Order to Max
        spoon1 = self._make_order(self.wooden_spoon,   self.shelfB, 20, 24, 30,  6)
        # Order
        spoon2 = self._make_order(self.steel_spoon,    self.shelfA, 30, 36, 45,  9)
        spoon3 = self._make_order(self.steel_spoon,    self.shelfB, 40, 48, 60, 12)
        # Order to Max
        spoon4 = self._make_order(self.plastic_spoon,  self.shelfA, 50, 60, 75, 15)
        spoon5 = self._make_order(self.plastic_spoon,  self.shelfB, 60, 72, 90, 18)
        # Snooze
        spoon6 = self._make_order(self.wooden_spoon,   self.shelfC,  5, 10, 15,  2)
        spoon7 = self._make_order(self.steel_spoon,    self.shelfC,  5, 10, 15,  2)
        spoon8 = self._make_order(self.plastic_spoon,  self.shelfC,  5, 10, 15,  2)
        # Unrelated product - must not appear in Spoon reordering rules
        knife0 = self._make_order(self.knife,          self.shelfA,  5, 10, 15,  2)

        self.start_tour(self._get_product_url(self.spoon.id), 'test_orderpoint_product_view_buttons', login='admin', step_delay=200)
        self.env['procurement.group'].run_scheduler()

        # Order
        self.assertTrue(self._check_replenishment_move(spoon0, 3))
        # Order to Max
        self.assertTrue(self._check_replenishment_move(spoon1, 10))
        # Snooze, 1 day
        self.assertEqual(spoon6['orderpoint'].snoozed_until, date.today() + timedelta(days=1))

        # Order in batch
        self.assertTrue(self._check_replenishment_move(spoon2, 9))
        self.assertTrue(self._check_replenishment_move(spoon3, 12))
        # Order to Max in batch
        self.assertTrue(self._check_replenishment_move(spoon4, 25))
        self.assertTrue(self._check_replenishment_move(spoon5, 30))
        # Snooze in batch, 1 week
        self.assertEqual(spoon7['orderpoint'].snoozed_until, date.today() + timedelta(weeks=1))
        self.assertEqual(spoon8['orderpoint'].snoozed_until, date.today() + timedelta(weeks=1))
