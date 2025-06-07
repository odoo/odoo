# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged
from odoo import Command


@tagged('post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Ensure minimum rights (avoid new groups added through modules installation)
        group_internal_user = cls.env.ref('base.group_user')
        group_pos_user = cls.env.ref('point_of_sale.group_pos_user')
        cls.pos_user.groups_id = [Command.set([group_internal_user.id, group_pos_user.id])]

        categ = cls.env.ref('product.product_category_all')

        cls.basic_kit, cls.finished, cls.component_a, cls.component_b = cls.env['product.product'].create([{
            'name': name,
            'type': 'consu',
            'is_storable': True,
            'categ_id': categ.id,
            'available_in_pos': True,
            'list_price': 10.0,
            'standard_price': 1.0,
            'taxes_id': False,
        } for name in ['Basic Kit', 'Finished', 'Component A', 'Component B']])

        cls.simple_kit_bom, cls.finished_bom = cls.env['mrp.bom'].create([{
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': bom_type,
            'bom_line_ids': [
                Command.create({
                    'product_id': cls.component_a.id,
                    'product_qty': 1,
                }),
                Command.create({
                    'product_id': cls.component_b.id,
                    'product_qty': 1,
                }),
            ],
        } for product, bom_type in [
            (cls.basic_kit, 'phantom'),
            (cls.finished, 'normal'),
        ]])

    def test_ship_later_kit_and_mto_manufactured_product(self):
        """
        Ship Later PoS. Sell a kit and a manufactured product. Before selling
        them, the PoS user reads their product information. The second one has
        both MTO and manufacture routes. Once sold, the delivery should contain
        the manufactured product and the kit's components. Thanks to the routes,
        there should also be a MO for the manufactured product.
        """
        self.main_pos_config.write({
            'ship_later': True,
        })

        mto_route = self.env.ref('stock.route_warehouse0_mto')
        manu_route = self.env.ref('mrp.route_warehouse0_manufacture')
        mto_route.active = True
        self.finished.route_ids = [Command.set((mto_route | manu_route).ids)]

        customer = self.env['res.partner'].search([('email', '=', 'partner.full@example.com')], limit=1)
        customer.name = "AAAA Super Customer"

        self.main_pos_config.with_user(self.pos_user).open_ui()
        url = "/pos/ui?config_id=%d" % self.main_pos_config.id
        self.start_tour(url, 'test_ship_later_kit_and_mto_manufactured_product', login="pos_user")

        picking = self.env['stock.picking'].search([('partner_id', '=', self.partner_full.id)], limit=1)
        self.assertRecordValues(picking.move_ids, [
            {'product_id': self.finished.id, 'product_qty': 1.0},
            {'product_id': self.component_a.id, 'product_qty': 1.0},
            {'product_id': self.component_b.id, 'product_qty': 1.0},
        ])

        finished_sm = picking.move_ids[0]
        self.assertEqual(finished_sm.move_orig_ids.production_id.product_id, self.finished)
