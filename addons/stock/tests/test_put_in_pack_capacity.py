# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPutInPackCapacity(TransactionCase):
    """ Herbs stocked by kg and shipped in big paper bags (0.1176 m3 each, 0.3 kg), 21 bags per pallet: the number of
    pallets comes from the volume of the bags, not from the weight of the herbs. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref('stock.group_tracking_lot') | cls.env.ref('stock.group_production_lot') | cls.env.ref('uom.group_uom')
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')
        cls.bag_type, cls.pallet_type = cls.env['stock.package.type'].create([
            {'name': 'Big paper bag', 'base_weight': 0.3, 'packaging_length': 350, 'width': 350, 'height': 960.38},
            {'name': 'Pallet', 'sequence_code': 'PAL', 'base_weight': 20, 'max_weight': 600, 'max_volume': 2.48},
        ])
        cls.uom_bag_9, cls.uom_bag_25 = cls.env['uom.uom'].create([
            {'name': f'x {size} kg', 'relative_factor': size, 'relative_uom_id': cls.uom_kg.id, 'package_type_id': cls.bag_type.id}
            for size in (9, 25)
        ])
        cls.nettle, cls.st_johns_wort = cls.env['product.product'].create([
            {'name': name, 'is_storable': True, 'tracking': 'lot', 'uom_id': cls.uom_kg.id, 'weight': 1.0, 'uom_ids': [Command.set(uom.ids)]}
            for name, uom in (('Nettle', cls.uom_bag_9), ('St John\'s wort', cls.uom_bag_25))
        ])
        cls.picking_type_out = cls.warehouse.out_type_id
        cls.customer = cls.env['res.partner'].create({'name': 'Herbal shop'})

    def _create_delivery(self, *lines):
        """ lines: (product, packaging, number of packagings, lot name) """
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_out.id,
            'partner_id': self.customer.id,
            'move_ids': [Command.create({
                'product_id': product.id,
                'product_uom_qty': packaging.relative_factor * count,
                'uom_id': self.uom_kg.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            }) for product, packaging, count, __ in lines],
        })
        for move, (__, packaging, __, __) in zip(picking.move_ids, lines):
            # The packaging comes from the sale or purchase order line.
            move.packaging_uom_id = packaging
        for product, packaging, count, lot_name in lines:
            lot = self.env['stock.lot'].create({'name': lot_name, 'product_id': product.id})
            self.env['stock.quant']._update_available_quantity(product, self.stock_location, packaging.relative_factor * count, lot_id=lot)
        picking.action_confirm()
        picking.action_assign()
        return picking

    def _wizard(self, picking):
        return Form(self.env['stock.put.in.pack'].with_context(
            default_move_line_ids=picking.move_line_ids.ids,
            default_location_dest_id=picking.location_dest_id.id,
            all_move_line_ids=picking.move_line_ids.ids,
        ))

    def _put_in_pallets(self, picking):
        wizard = self._wizard(picking)
        wizard.package_type_id = self.pallet_type
        self.assertTrue(wizard.split_by_capacity)
        wizard.save().action_put_in_pack()
        return picking.move_line_ids.result_package_id

    def test_pallets_by_volume(self):
        """ 42 bags of 9 kg of nettle: 2 pallets of 21 bags, named by the sequence of the pallet type. """
        picking = self._create_delivery((self.nettle, self.uom_bag_9, 42, 'NM-B619'))
        pallets = self._put_in_pallets(picking)

        self.assertEqual(len(pallets), 2)
        self.assertTrue(all(name.startswith('PAL') for name in pallets.mapped('name')))
        self.assertRecordValues(picking.move_line_ids.sorted('id'), [
            {'quantity': 189, 'lot_id': picking.move_line_ids.lot_id.id},
            {'quantity': 189, 'lot_id': picking.move_line_ids.lot_id.id},
        ])
        self.assertEqual(picking.move_ids.quantity, 378)

    def test_mixed_pallet_keeps_lines_whole(self):
        """ 9 bags of nettle and 12 bags of St John's wort fit on one pallet: the lines are not split. """
        picking = self._create_delivery(
            (self.nettle, self.uom_bag_9, 9, 'NM-B619'),
            (self.st_johns_wort, self.uom_bag_25, 12, 'OF-A100'),
        )
        pallets = self._put_in_pallets(picking)
        self.assertEqual(len(pallets), 1)
        self.assertEqual(len(picking.move_line_ids), 2)

    def test_pallets_by_weight(self):
        """ 30 bags of 25 kg of St John's wort: 600 kg per pallet allow 23 bags (25.3 kg each), but the volume only 21. """
        picking = self._create_delivery((self.st_johns_wort, self.uom_bag_25, 30, 'OF-A100'))
        self.pallet_type.max_weight = 400  # 15 bags of 25.3 kg
        pallets = self._put_in_pallets(picking)
        self.assertEqual(len(pallets), 2)
        self.assertEqual(sorted(picking.move_line_ids.mapped('quantity')), [375, 375])

    def test_without_split_by_capacity(self):
        """ Without the option, all the lines go to one package, as before. """
        picking = self._create_delivery((self.nettle, self.uom_bag_9, 42, 'NM-B619'))
        wizard = self._wizard(picking)
        wizard.package_type_id = self.pallet_type
        wizard.split_by_capacity = False
        wizard.save().action_put_in_pack()
        self.assertEqual(len(picking.move_line_ids.result_package_id), 1)

    def test_unit_too_big(self):
        self.pallet_type.max_weight = 5
        picking = self._create_delivery((self.nettle, self.uom_bag_9, 2, 'NM-B619'))
        with self.assertRaises(UserError):
            picking.move_line_ids.action_put_in_pack(package_type_id=self.pallet_type.id, split_by_capacity=True)
