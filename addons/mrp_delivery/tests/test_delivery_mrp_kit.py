# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged('post_install', '-at_install')
class TestDeliveryMrpKitBom(BaseCommon):

    def test_sale_mrp_kit_sale_price_with_different_uoms(self):
        """Check the total sale price of a KIT:
            # BoM of Kit A:
                # - BoM Type: Kit
                # - Quantity: 1
                # - Components:
                # * 1 x Component A (Price: $ 8, QTY: 10, UOM: Meter)
                # * 1 x Component B (Price: $ 5, QTY: 2, UOM: Dozen)
            # sale price of Kit A = (8 * 10) + (5 * 2 * 12) = $ 200
        """

        customer = self.env['res.partner'].create({'name': 'customer'})
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company)], limit=1)
        kit_product, component_a, component_b = self.env['product.product'].create([
            {
                'name': name,
                'is_storable': True,
                'standard_price': 1.0,
                'lst_price': price,
            } for (name, price) in zip(('Kit Product', 'Component A', 'Component B'), (200, 0.08, 5))
        ])
        component_a.uom_id = self.ref('uom.product_uom_cm')
        self.env['stock.quant']._update_available_quantity(component_a, warehouse.lot_stock_id, 1000)
        self.env['stock.quant']._update_available_quantity(component_b, warehouse.lot_stock_id, 24)
        self.bom = self.env['mrp.bom'].create({
            'product_tmpl_id': kit_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({
                    'product_id': component_a.id,
                    'product_qty': 10.0,
                    'product_uom_id': self.ref('uom.product_uom_meter'),
                }),
                Command.create({
                    'product_id': component_b.id,
                    'product_qty': 2.0,
                    'product_uom_id': self.ref('uom.product_uom_dozen'),
                }),
            ]
        })

        # Create a SO with one unit of the kit product
        so = self.env['sale.order'].create({
            'partner_id': customer.id,
            'order_line': [
                Command.create({
                    'name': kit_product.name,
                    'product_id': kit_product.id,
                    'product_uom_qty': 1.0,
                    'product_uom_id': kit_product.uom_id.id,
                })],
            'warehouse_id': warehouse.id,
        })
        so.action_confirm()
        so.picking_ids.button_validate()
        move_lines = so.picking_ids.move_ids.move_line_ids
        self.assertEqual(move_lines.mapped("sale_price"), [92, 138], 'wrong shipping value')
        self.assertEqual(sum(move_lines.mapped("sale_price")), so.order_line.price_total)

    def test_sale_price_repartition_on_kit_product(self):
        """
        Kit products can be sold as a bundle carring a diffrent price than
        the sum of its component prices. This test ensures that the bundle
        price is then distributed proportionally on the components.
        Sale order:
            - 1 x Compo 1, price 20
            - 2 x Kit 1 price unit 120 instead of 150:
                - 1 x Service product, price 10
                - 1 x Compo 1, price 20
                - 1 x Give away, price 0
                - 2 x Kit 2, exploded price 2 x 60 = 120
            - 6 x Kit 2 price unit 50 instead of 60:
                - 1 x Service product, price 10
                - 1 x Compo 1, price 20
                - 1 x Compo 2, price 30
        """

        kit_1, kit_2, component_1, component_2, give_away, service = self.env['product.product'].create([
            {
                'name': name,
                'list_price': price,
                'type': product_type,
                'is_storable': product_type == 'consu',
            } for name, price, product_type in [
                ('Lovely Kit 1', 120.0, 'consu'),
                ('Lovely Kit 2', 50.0, 'consu'),
                ('Lovely Comp 1', 20.0, 'consu'),
                ('Lovely Comp 2', 30.0, 'consu'),
                ('Give away', 0.0, 'consu'),
                ('Lovely Service', 10.0, 'service'),
            ]
        ])
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        for product in [component_1, component_2, give_away]:
            self.env['stock.quant']._update_available_quantity(product, warehouse.lot_stock_id, quantity=20.0)
        self.env['mrp.bom'].create([
            {
                'product_tmpl_id': kit_1.product_tmpl_id.id,
                'product_qty': 1,
                'type': 'phantom',
                'bom_line_ids': [
                    Command.create({'product_id': service.id, 'product_qty': 1}),
                    Command.create({'product_id': component_1.id, 'product_qty': 1}),
                    Command.create({'product_id': give_away.id, 'product_qty': 1}),
                    Command.create({'product_id': kit_2.id, 'product_qty': 2}),
                ],
            },
            {
                'product_tmpl_id': kit_2.product_tmpl_id.id,
                'product_qty': 1,
                'type': 'phantom',
                'bom_line_ids': [
                    Command.create({'product_id': service.id, 'product_qty': 1}),
                    Command.create({'product_id': component_1.id, 'product_qty': 1}),
                    Command.create({'product_id': component_2.id, 'product_qty': 1}),
                ],
            },
        ])
        customer = self.env['res.partner'].create({
            'name': 'customer',
        })
        so = self.env['sale.order'].create({
            'partner_id': customer.id,
            'order_line': [
                Command.create({'product_id': component_1.id, 'product_uom_qty': 2.0}),
                Command.create({'product_id': kit_1.id, 'product_uom_qty': 2.0}),
                Command.create({'product_id': kit_2.id, 'product_uom_qty': 1.0, 'product_uom_id': self.ref('uom.product_uom_pack_6')}),
            ],
        })
        so.action_confirm()
        self.assertEqual(so.order_line.mapped('price_total'), [46, 276, 345.0])
        self.assertRecordValues(so.picking_ids.move_line_ids.sorted(lambda ml: (ml.move_id.sale_line_id.id, ml.product_id.id)), [
            {'product_id': component_1.id, 'quantity': 2.0, 'sale_price': 46.0},  # sol1 direct comp1
            {'product_id': component_1.id, 'quantity': 2.0, 'sale_price': 36.8},  # sol2 comp1 from kit 1
            {'product_id': component_1.id, 'quantity': 4.0, 'sale_price': 73.6},  # sol2 comp1 from kit 1 > kit 2
            {'product_id': component_2.id, 'quantity': 4.0, 'sale_price': 110.4},  # sol2 comp2 from kit 1 > kit 2
            {'product_id': give_away.id, 'quantity': 2.0, 'sale_price': 0.0},  # sol2 give away from kit 1
            {'product_id': component_1.id, 'quantity': 6.0, 'sale_price': 115.0},  # sol3 comp1 from kit 2
            {'product_id': component_2.id, 'quantity': 6.0, 'sale_price': 172.5},  # sol3  comp2 from kit 2
        ])
