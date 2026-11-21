# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestFreightQuotation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref('stock.group_tracking_lot') | cls.env.ref('uom.group_uom') | cls.env.ref('purchase.group_purchase_manager')
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')
        cls.pallet_type = cls.env['stock.package.type'].create({
            'name': 'Pallet 1 x 1.4 x 1.8 m',
            'packaging_length': 1000, 'width': 1400, 'height': 1800,
            'max_weight': 600, 'stackable': False,
        })
        cls.uom_bag = cls.env['uom.uom'].create({'name': 'Bag of 14 kg', 'relative_factor': 14, 'relative_uom_id': cls.uom_kg.id})
        cls.herb = cls.env['product.product'].create({
            'name': 'Yarrow', 'is_storable': True, 'uom_id': cls.uom_kg.id, 'uom_ids': [Command.set(cls.uom_bag.ids)], 'weight': 1.0,
        })
        cls.customer = cls.env['res.partner'].create({'name': 'Herbal shop', 'street': 'Fo utca 1', 'city': 'Budapest', 'zip': '1011'})
        cls.carrier = cls.env['res.partner'].create({'name': 'Carrier Ltd'})
        cls.env['stock.quant']._update_available_quantity(cls.herb, cls.warehouse.lot_stock_id, 5000)

    def _create_delivery(self):
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.out_type_id.id,
            'partner_id': self.customer.id,
            'move_ids': [Command.create({
                'product_id': self.herb.id,
                'product_uom_qty': 2268,
                'uom_id': self.uom_kg.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            })],
        })
        picking.move_ids.packaging_uom_id = self.uom_bag  # from the sale order line
        picking.action_confirm()
        picking.action_assign()
        # Two pallets
        line = picking.move_line_ids
        pallets = self.env['stock.package'].create([{'package_type_id': self.pallet_type.id} for _i in range(2)])
        line.copy({'quantity': 1134, 'result_package_id': pallets[1].id})
        line.write({'quantity': 1134, 'result_package_id': pallets[0].id})
        return picking

    def test_load_summary(self):
        summary = self._create_delivery()._get_load_summary()
        self.assertEqual(summary['quantities'], {self.uom_kg: 2268})
        self.assertEqual(summary['packagings'], {self.uom_bag: 162})
        self.assertEqual(len(summary['packages']), 1)
        self.assertEqual(summary['packages'][0]['package_type'], self.pallet_type)
        self.assertEqual(summary['packages'][0]['count'], 2)
        self.assertAlmostEqual(summary['floor_area'], 2.8)

    def test_request_freight_quotation(self):
        pickings = self._create_delivery() | self._create_delivery()
        self.assertFalse(self.env.company.freight_product_id)
        action = pickings.action_request_freight_quotation()
        freight_product = self.env.company.freight_product_id
        self.assertTrue(freight_product)

        with Form(self.env['purchase.order'].with_context(action['context'])) as order_form:
            order_form.partner_id = self.carrier
        order = order_form.record

        self.assertEqual(order.origin, ', '.join(pickings.mapped('name')))
        self.assertEqual(order.order_line.product_id, freight_product)
        self.assertEqual(len(order.order_line), 2)
        for picking, line in zip(pickings, order.order_line):
            self.assertIn(picking.name, line.name)
            self.assertIn('2268 kg', line.name)
            self.assertIn('162 x Bag of 14 kg', line.name)
            self.assertIn('2 x Pallet 1 x 1.4 x 1.8 m (1000 x 1400 x 1800 mm, max. 600 kg, not stackable)', line.name)
            self.assertIn('Budapest', line.name)
        self.assertIn('4 x Pallet 1 x 1.4 x 1.8 m', order.note)
        self.assertIn('5.60', order.note)

        # The descriptions are kept when the order is sent to another carrier.
        names = order.order_line.mapped('name')
        order.partner_id = self.env['res.partner'].create({'name': 'Other carrier'})
        self.assertEqual(order.order_line.mapped('name'), names)

        # The freight product is reused.
        pickings.action_request_freight_quotation()
        self.assertEqual(self.env.company.freight_product_id, freight_product)
