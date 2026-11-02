# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestDeliveryPackaging(TransactionCase):
    """ A product sold by kg and shipped in bags of 9 kg: the weight and volume of the shipment come
    from the package type of the packaging (tare and dimensions), not only from the product. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')
        cls.bag_type = cls.env['stock.package.type'].create({
            'name': 'Paper bag',
            'base_weight': 0.3,
            'packaging_length': 500.0,
            'width': 400.0,
            'height': 600.0,  # 0.12 m³
        })
        cls.uom_bag = cls.env['uom.uom'].create({
            'name': 'x 9 kg',
            'relative_factor': 9.0,
            'relative_uom_id': cls.uom_kg.id,
            'package_type_id': cls.bag_type.id,
        })
        cls.uom_box = cls.env['uom.uom'].create({
            'name': 'x 10 kg (no package type)',
            'relative_factor': 10.0,
            'relative_uom_id': cls.uom_kg.id,
        })
        cls.nettle = cls.env['product.product'].create({
            'name': 'Nettle',
            'is_storable': True,
            'uom_id': cls.uom_kg.id,
            'uom_ids': [Command.set((cls.uom_bag | cls.uom_box).ids)],
            'weight': 1.0,
            'volume': 0.01,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Herbal shop'})
        delivery_product = cls.env['product.product'].create({'name': 'Delivery', 'type': 'service'})
        cls.carrier_weight, cls.carrier_volume = cls.env['delivery.carrier'].create([
            {
                'name': f'Price per {variable}',
                'delivery_type': 'base_on_rule',
                'product_id': delivery_product.id,
                'price_rule_ids': [Command.create({
                    'variable': 'price',
                    'operator': '>=',
                    'max_value': 0,
                    'list_price': 1.0,
                    'variable_factor': variable,
                })],
            }
            for variable in ('weight', 'volume')
        ])

    def _create_order(self, quantity, uom):
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': self.nettle.id,
                'product_uom_qty': quantity,
                'product_uom_id': uom.id,
            })],
        })

    def test_shipping_weight_and_volume(self):
        for quantity, uom, weight, volume in (
            # 3 bags: 27 kg + 3 x 0.3 kg, 3 x 0.12 m³
            (3, self.uom_bag, 27.9, 0.36),
            # 2.5 bags: 22.5 kg in 3 bags
            (2.5, self.uom_bag, 23.4, 0.36),
            # no packaging: the product weight and volume, as before
            (27, self.uom_kg, 27.0, 0.27),
            # packaging without package type: as before
            (3, self.uom_box, 30.0, 0.3),
        ):
            with self.subTest(quantity=quantity, uom=uom.name):
                shipping_weight, shipping_volume = self.nettle._get_shipping_weight_and_volume(quantity, uom)
                self.assertAlmostEqual(shipping_weight, weight)
                self.assertAlmostEqual(shipping_volume, volume)

    def test_delivery_price_from_packaging(self):
        order = self._create_order(3, self.uom_bag)
        self.assertAlmostEqual(self.carrier_weight._get_price_available(order), 27.9)
        self.assertAlmostEqual(self.carrier_volume._get_price_available(order), 0.36)
        self.assertAlmostEqual(order._get_estimated_weight(), 27.9)

        order_kg = self._create_order(27, self.uom_kg)
        self.assertAlmostEqual(self.carrier_weight._get_price_available(order_kg), 27.0)
        self.assertAlmostEqual(self.carrier_volume._get_price_available(order_kg), 0.27)

    def test_picking_weight_and_volume_from_packaging(self):
        stock_location = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1).lot_stock_id
        self.env['stock.quant']._update_available_quantity(self.nettle, stock_location, 100)
        order = self._create_order(3, self.uom_bag)
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context(
            default_order_id=order.id, default_carrier_id=self.carrier_weight.id,
        ))
        delivery_wizard.save().button_confirm()
        order.action_confirm()
        picking = order.picking_ids
        picking.action_assign()

        self.assertEqual(picking.move_ids.packaging_uom_id, self.uom_bag)
        self.assertAlmostEqual(picking.move_ids.weight, 27.9)
        self.assertAlmostEqual(picking.weight, 27.9)
        self.assertAlmostEqual(picking.shipping_weight, 27.9)
        self.assertAlmostEqual(picking.shipping_volume, 0.36)
        self.assertAlmostEqual(picking._get_estimated_weight(), 27.9)
