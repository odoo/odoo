# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests.common import TransactionCase


class TestAutoWaving(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.child_location_1 = cls.env['stock.location'].create({
            'name': 'Sub Location 1',
            'location_id': cls.stock_location.id,
        })
        cls.child_location_2 = cls.env['stock.location'].create({
            'name': 'Sub Location 2',
            'location_id': cls.stock_location.id,
        })
        cls.grandchild_location = cls.env['stock.location'].create({
            'name': 'Grandchild Location',
            'location_id': cls.child_location_1.id,
        })
        cls.sibling_location = cls.env['stock.location'].create({
            'name': 'Sibling Location',
            'location_id': cls.stock_location.location_id.id,
        })

        cls.product_1 = cls.env['product.product'].create({
            'name': 'Product 1',
            'is_storable': True,
        })
        cls.product_2 = cls.env['product.product'].create({
            'name': 'Product 2',
            'is_storable': True,
        })
        cls.product_3 = cls.env['product.product'].create({
            'name': 'Product 3',
            'is_storable': True,
        })
        cls.product_4 = cls.env['product.product'].create({
            'name': 'Product 4',
            'is_storable': True,
        })

        Quant = cls.env['stock.quant']

        Quant._update_available_quantity(cls.product_1, cls.stock_location, 2)
        Quant._update_available_quantity(cls.product_1, cls.child_location_1, 6)
        Quant._update_available_quantity(cls.product_1, cls.child_location_2, 6)
        Quant._update_available_quantity(cls.product_1, cls.grandchild_location, 3)

        Quant._update_available_quantity(cls.product_2, cls.child_location_1, 4)
        Quant._update_available_quantity(cls.product_2, cls.child_location_2, 2)
        Quant._update_available_quantity(cls.product_2, cls.sibling_location, 2)

        Quant._update_available_quantity(cls.product_3, cls.grandchild_location, 3)

        Quant._update_available_quantity(cls.product_4, cls.child_location_1, 3)

        cls.picking_type_out = cls.env.ref('stock.picking_type_out')

        cls.us_client = cls.env['res.partner'].create({
            'name': 'US Client',
            'country_id': cls.env.ref('base.us').id,
        })
        cls.be_client = cls.env['res.partner'].create({
            'name': 'BE Client',
            'country_id': cls.env.ref('base.be').id,
        })
        cls.fr_client = cls.env['res.partner'].create({
            'name': 'FR Client',
            'country_id': cls.env.ref('base.fr').id,
        })
        cls.demo_partners = cls.us_client | cls.be_client | cls.fr_client

        cls.picking_1 = cls.env['stock.picking'].create({
            'location_id': cls.stock_location.id,
            'picking_type_id': cls.picking_type_out.id,
            'partner_id': cls.us_client.id,
            'move_ids': [
                Command.create({
                    'name': cls.product_1.name,
                    'product_id': cls.product_1.id,
                    'product_uom_qty': 3,
                    'product_uom': cls.product_1.uom_id.id,
                    'location_id': cls.child_location_1.id,
                }),
                Command.create({
                    'name': cls.product_1.name,
                    'product_id': cls.product_1.id,
                    'product_uom_qty': 2,
                    'product_uom': cls.product_1.uom_id.id,
                    'location_id': cls.child_location_2.id,
                }),
                Command.create({
                    'name': cls.product_2.name,
                    'product_id': cls.product_2.id,
                    'product_uom_qty': 2,
                    'product_uom': cls.product_2.uom_id.id,
                    'location_id': cls.child_location_1.id,
                })
            ]
        })
        cls.picking_2 = cls.env['stock.picking'].create({
            'location_id': cls.stock_location.id,
            'picking_type_id': cls.picking_type_out.id,
            'partner_id': cls.be_client.id,
            'move_ids': [
                Command.create({
                    'name': cls.product_1.name,
                    'product_id': cls.product_1.id,
                    'product_uom_qty': 3,
                    'product_uom': cls.product_1.uom_id.id,
                    'location_id': cls.grandchild_location.id,
                }),
                Command.create({
                    'name': cls.product_1.name,
                    'product_id': cls.product_1.id,
                    'product_uom_qty': 2,
                    'product_uom': cls.product_1.uom_id.id,
                    'location_id': cls.child_location_2.id,
                }),
                Command.create({
                    'name': cls.product_2.name,
                    'product_id': cls.product_2.id,
                    'product_uom_qty': 2,
                    'product_uom': cls.product_2.uom_id.id,
                    'location_id': cls.child_location_1.id,
                })
            ]
        })
        cls.picking_3 = cls.env['stock.picking'].create({
            'location_id': cls.stock_location.id,
            'picking_type_id': cls.picking_type_out.id,
            'partner_id': cls.us_client.id,
            'move_ids': [
                Command.create({
                    'name': cls.product_1.name,
                    'product_id': cls.product_1.id,
                    'product_uom_qty': 2,
                    'product_uom': cls.product_1.uom_id.id,
                    'location_id': cls.stock_location.id,
                }),
                Command.create({
                    'name': cls.product_2.name,
                    'product_id': cls.product_2.id,
                    'product_uom_qty': 2,
                    'product_uom': cls.product_2.uom_id.id,
                    'location_id': cls.child_location_2.id,
                }),
                Command.create({
                    'name': cls.product_3.name,
                    'product_id': cls.product_3.id,
                    'product_uom_qty': 3,
                    'product_uom': cls.product_3.uom_id.id,
                    'location_id': cls.grandchild_location.id,
                })
            ]
        })
        cls.picking_4 = cls.env['stock.picking'].create({
            'location_id': cls.stock_location.id,
            'picking_type_id': cls.picking_type_out.id,
            'partner_id': cls.be_client.id,
            'move_ids': [
                Command.create({
                    'name': cls.product_4.name,
                    'product_id': cls.product_4.id,
                    'product_uom_qty': 3,
                    'product_uom': cls.product_4.uom_id.id,
                    'location_id': cls.child_location_1.id,
                })
            ]
        })
        cls.picking_5 = cls.env['stock.picking'].create({
            'location_id': cls.stock_location.id,
            'picking_type_id': cls.picking_type_out.id,
            'partner_id': cls.fr_client.id,
            'move_ids': [
                Command.create({
                    'name': cls.product_1.name,
                    'product_id': cls.product_1.id,
                    'product_uom_qty': 3,
                    'product_uom': cls.product_1.uom_id.id,
                    'location_id': cls.child_location_1.id,
                }),
                Command.create({
                    'name': cls.product_1.name,
                    'product_id': cls.product_1.id,
                    'product_uom_qty': 2,
                    'product_uom': cls.product_1.uom_id.id,
                    'location_id': cls.child_location_2.id,
                }),
                Command.create({
                    'name': cls.product_2.name,
                    'product_id': cls.product_2.id,
                    'product_uom_qty': 2,
                    'product_uom': cls.product_2.uom_id.id,
                    'location_id': cls.sibling_location.id,
                })
            ]
        })
        cls.all_pickings = cls.picking_1 | cls.picking_2 | cls.picking_3 | cls.picking_4 | cls.picking_5

    def test_group_by_partner_and_location(self):
        self.picking_type_out.write({
            'auto_batch': True,
            'batch_group_by_partner': True,
            'wave_group_by_location': True,
            'wave_location_ids': self.child_location_2,
            'batch_group_by_destination': False,
            'batch_group_by_src_loc': False,
            'batch_group_by_dest_loc': False,
            'wave_group_by_product': False,
            'wave_group_by_category': False,
        })

        self.all_pickings.action_assign()

        all_batches = self.env['stock.picking.batch'].search([('picking_ids.partner_id', 'in', self.demo_partners.ids)])
        waves = all_batches.filtered(lambda b: b.is_wave)

        wave_1 = waves.filtered(lambda w: w.description == f'{self.us_client.name}, {self.child_location_2.complete_name}')
        self.assertEqual(len(wave_1), 1)
        self.assertEqual(len(wave_1.picking_ids), 2)
        self.assertEqual(len(wave_1.move_line_ids), 2)
        self.assertEqual(wave_1.picking_ids.partner_id, self.us_client)
        self.assertEqual(wave_1.move_line_ids.location_id, self.child_location_2)

        wave_2 = waves.filtered(lambda w: w.description == f'{self.be_client.name}, {self.child_location_2.complete_name}')
        self.assertEqual(len(wave_2), 1)
        self.assertEqual(len(wave_2.picking_ids), 1)
        self.assertEqual(len(wave_2.move_line_ids), 1)
        self.assertEqual(wave_2.picking_ids.partner_id, self.be_client)
        self.assertEqual(wave_2.move_line_ids.location_id, self.child_location_2)

        wave_3 = waves.filtered(lambda w: w.description == f'{self.fr_client.name}, {self.child_location_2.complete_name}')
        self.assertEqual(len(wave_3), 1)
        self.assertEqual(len(wave_3.picking_ids), 1)
        self.assertEqual(len(wave_3.move_line_ids), 1)
        self.assertEqual(wave_3.picking_ids.partner_id, self.fr_client)
        self.assertEqual(wave_3.move_line_ids.location_id, self.child_location_2)

        batches = all_batches - waves
        batch_1 = batches.filtered(lambda b: b.description == self.us_client.name)
        self.assertEqual(len(batch_1), 1)
        self.assertEqual(len(batch_1.picking_ids), 2)
        self.assertEqual(len(batch_1.move_line_ids), 4)
        self.assertEqual(batch_1.picking_ids.partner_id, self.us_client)
        self.assertEqual(len(batch_1.move_line_ids.location_id), 3)

        batch_2 = batches.filtered(lambda b: b.description == self.be_client.name)
        self.assertEqual(len(batch_2), 1)
        self.assertEqual(len(batch_2.picking_ids), 2)
        self.assertEqual(len(batch_2.move_line_ids), 3)
        self.assertEqual(batch_2.picking_ids.partner_id, self.be_client)
        self.assertEqual(len(batch_2.move_line_ids.location_id), 2)

        batch_3 = batches.filtered(lambda b: b.description == self.fr_client.name)
        self.assertEqual(len(batch_3), 1)
        self.assertEqual(len(batch_3.picking_ids), 1)
        self.assertEqual(len(batch_3.move_line_ids), 2)
        self.assertEqual(batch_3.picking_ids.partner_id, self.fr_client)
        self.assertEqual(len(batch_3.move_line_ids.location_id), 2)

    def test_group_by_locations(self):
        self.picking_type_out.write({
            'auto_batch': True,
            'wave_group_by_location': True,
            'wave_location_ids': (self.stock_location | self.child_location_1).ids,
            'batch_group_by_partner': False,
            'batch_group_by_destination': False,
            'batch_group_by_src_loc': False,
            'batch_group_by_dest_loc': False,
            'wave_group_by_product': False,
            'wave_group_by_category': False,
        })

        self.all_pickings.action_assign()

        all_batches = self.env['stock.picking.batch'].search([('picking_ids.partner_id', 'in', self.demo_partners.ids)])
        waves = all_batches.filtered(lambda b: b.is_wave)

        wave_1 = waves.filtered(lambda w: w.description == self.child_location_1.complete_name)
        self.assertEqual(len(wave_1), 1)
        self.assertEqual(len(wave_1.picking_ids), 5)
        self.assertEqual(len(wave_1.move_line_ids), 7)
        self.assertEqual(len(wave_1.picking_ids.partner_id), 3)
        self.assertTrue(all(l._child_of(self.child_location_1) for l in wave_1.move_line_ids.location_id))

        wave_2 = waves.filtered(lambda w: w.description == self.stock_location.complete_name)
        self.assertEqual(len(wave_2), 1)
        self.assertEqual(len(wave_2.picking_ids), 4)
        self.assertEqual(len(wave_2.move_line_ids), 5)
        self.assertEqual(len(wave_2.picking_ids.partner_id), 3)
        self.assertTrue(all(l._child_of(self.stock_location) for l in wave_1.move_line_ids.location_id))

    def test_group_by_country_and_product(self):
        self.picking_type_out.write({
            'auto_batch': True,
            'batch_group_by_destination': True,
            'wave_group_by_product': True,
            'batch_group_by_partner': False,
            'batch_group_by_src_loc': False,
            'batch_group_by_dest_loc': False,
            'wave_group_by_category': False,
            'wave_group_by_location': False,
        })

        self.all_pickings.action_assign()

        all_batches = self.env['stock.picking.batch'].search([('picking_ids.partner_id', 'in', self.demo_partners.ids)])
        waves = all_batches.filtered(lambda b: b.is_wave)

        wave_1 = waves.filtered(lambda w: w.description == f'United States, {self.product_1.name}')
        self.assertEqual(len(wave_1), 1)
        self.assertEqual(len(wave_1.picking_ids), 2)
        self.assertEqual(len(wave_1.move_line_ids), 3)
        self.assertEqual(wave_1.picking_ids.partner_id, self.us_client)
        self.assertEqual(wave_1.move_line_ids.product_id, self.product_1)
        # Set the quantity of the move line that is the only one in the picking to 0
        # to check if it is correctly moved to another wave.
        self.assertCountEqual(wave_1.move_line_ids.mapped('quantity'), [2.0, 3.0, 2.0])
        modified_move_line = wave_1.picking_ids.filtered(lambda p: len(p.move_ids) == 1).move_line_ids
        modified_move_line.quantity = 0
        self.assertCountEqual(wave_1.move_line_ids.mapped('quantity'), [0.0, 3.0, 2.0])
        wave_1.action_done()
        self.assertEqual(wave_1.state, 'done')
        self.assertTrue(modified_move_line.batch_id.id)
        self.assertNotEqual(modified_move_line.batch_id, wave_1)

        wave_2 = waves.filtered(lambda w: w.description == f'United States, {self.product_2.name}')
        self.assertEqual(len(wave_2), 1)
        self.assertEqual(len(wave_2.picking_ids), 2)
        self.assertEqual(len(wave_2.move_line_ids), 2)
        self.assertEqual(wave_2.picking_ids.partner_id, self.us_client)
        self.assertEqual(wave_2.move_line_ids.product_id, self.product_2)

        wave_3 = waves.filtered(lambda w: w.description == f'United States, {self.product_3.name}')
        self.assertEqual(len(wave_3), 1)
        self.assertEqual(len(wave_3.picking_ids), 1)
        self.assertEqual(len(wave_3.move_line_ids), 1)
        self.assertEqual(wave_3.picking_ids.partner_id, self.us_client)
        self.assertEqual(wave_3.move_line_ids.product_id, self.product_3)

        wave_4 = waves.filtered(lambda w: w.description == f'Belgium, {self.product_1.name}')
        self.assertEqual(len(wave_4), 1)
        self.assertEqual(len(wave_4.picking_ids), 1)
        self.assertEqual(len(wave_4.move_line_ids), 2)
        self.assertEqual(wave_4.picking_ids.partner_id, self.be_client)
        self.assertEqual(wave_4.move_line_ids.product_id, self.product_1)

        wave_5 = waves.filtered(lambda w: w.description == f'Belgium, {self.product_2.name}')
        self.assertEqual(len(wave_5), 1)
        self.assertEqual(len(wave_5.picking_ids), 1)
        self.assertEqual(len(wave_5.move_line_ids), 1)
        self.assertEqual(wave_5.picking_ids.partner_id, self.be_client)
        self.assertEqual(wave_5.move_line_ids.product_id, self.product_2)

        wave_6 = waves.filtered(lambda w: w.description == f'Belgium, {self.product_4.name}')
        self.assertEqual(len(wave_6), 1)
        self.assertEqual(len(wave_6.picking_ids), 1)
        self.assertEqual(len(wave_6.move_line_ids), 1)
        self.assertEqual(wave_6.picking_ids.partner_id, self.be_client)
        self.assertEqual(wave_6.move_line_ids.product_id, self.product_4)

        wave_7 = waves.filtered(lambda w: w.description == f'France, {self.product_1.name}')
        self.assertEqual(len(wave_7), 1)
        self.assertEqual(len(wave_7.picking_ids), 1)
        self.assertEqual(len(wave_7.move_line_ids), 2)
        self.assertEqual(wave_7.picking_ids.partner_id, self.fr_client)
        self.assertEqual(wave_7.move_line_ids.product_id, self.product_1)

        wave_8 = waves.filtered(lambda w: w.description == f'France, {self.product_2.name}')
        self.assertEqual(len(wave_8), 1)
        self.assertEqual(len(wave_8.picking_ids), 1)
        self.assertEqual(len(wave_8.move_line_ids), 1)
        self.assertEqual(wave_8.picking_ids.partner_id, self.fr_client)
        self.assertEqual(wave_8.move_line_ids.product_id, self.product_2)

    def test_group_only_when_auto_batch_is_enable(self):
        """ This test ensures wave grouping is only done when the `auto_batch`
        field is true, no matter what the other fields value is."""
        # Update quantity in stock to have enough for fullfil all pickings and their copies.
        for location, products in [
            [self.stock_location, [self.product_1]],
            [self.child_location_1, [self.product_1, self.product_2, self.product_4]],
            [self.child_location_2, [self.product_1, self.product_2]],
            [self.grandchild_location, [self.product_1, self.product_3]],
        ]:
            for product in products:
                self.env['stock.quant']._update_available_quantity(product, location, 99)
        # Set `wave_group_by_product` on true even if `auto_batch` is false.
        self.picking_type_out.write({
            'auto_batch': False,
            'batch_group_by_destination': False,
            'batch_group_by_partner': False,
            'batch_group_by_src_loc': False,
            'batch_group_by_dest_loc': False,
            'wave_group_by_category': False,
            'wave_group_by_location': False,
            'wave_group_by_product': True,
        })
        # Auto batch is disabled -> pickings' products shouldn't be batched in wave.
        all_pickings_copy = self.all_pickings.copy()
        all_pickings_copy.action_assign()
        waves = self.env['stock.picking.batch'].search([('is_wave', '=', True)])
        self.assertEqual(len(waves), 0)
        # Set auto batch on true -> pickings' products should be batched in wave.
        self.picking_type_out.auto_batch = True
        self.all_pickings.action_assign()
        waves = self.env['stock.picking.batch'].search([('is_wave', '=', True)])
        self.assertEqual(len(waves), 4)
