# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import common, Form
from odoo.exceptions import UserError


class TestMrpMulticompany(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.group_user').write({'implied_ids': [(4, cls.env.ref('stock.group_production_lot').id)]})

        group_user = cls.env.ref('base.group_user')
        group_mrp_manager = cls.env.ref('mrp.group_mrp_manager')
        cls.company_a = cls.env['res.company'].create({'name': 'Company A'})
        cls.company_b = cls.env['res.company'].create({'name': 'Company B'})
        cls.warehouse_a = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_a.id)], limit=1)
        cls.warehouse_b = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_b.id)], limit=1)
        cls.stock_location_a = cls.warehouse_a.lot_stock_id
        cls.stock_location_b = cls.warehouse_b.lot_stock_id

        cls.user_a = cls.env['res.users'].create({
            'name': 'user company a with access to company b',
            'login': 'user a',
            'groups_id': [(6, 0, [group_user.id, group_mrp_manager.id])],
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id, cls.company_b.id])]
        })
        cls.user_b = cls.env['res.users'].create({
            'name': 'user company a with access to company b',
            'login': 'user b',
            'groups_id': [(6, 0, [group_user.id, group_mrp_manager.id])],
            'company_id': cls.company_b.id,
            'company_ids': [(6, 0, [cls.company_a.id, cls.company_b.id])]
        })

    def test_bom_1(self):
        """Check it is not possible to use a product of Company B in a
        bom of Company A. """

        product_b = self.env['product.product'].create({
            'name': 'p1',
            'company_id': self.company_b.id,
        })
        with self.assertRaises(UserError):
            self.env['mrp.bom'].create({
                'product_id': product_b.id,
                'product_tmpl_id': product_b.product_tmpl_id.id,
                'company_id': self.company_a.id,
            })

    def test_bom_2(self):
        """Check it is not possible to use a product of Company B as a component
        in a bom of Company A. """

        product_a = self.env['product.product'].create({
            'name': 'p1',
            'company_id': self.company_a.id,
        })
        product_b = self.env['product.product'].create({
            'name': 'p2',
            'company_id': self.company_b.id,
        })
        with self.assertRaises(UserError):
            self.env['mrp.bom'].create({
                'product_id': product_a.id,
                'product_tmpl_id': product_b.product_tmpl_id.id,
                'company_id': self.company_a.id,
                'bom_line_ids': [(0, 0, {'product_id': product_b.id})]
            })

    def test_production_1(self):
        """Check it is not possible to confirm a production of Company B with
        product of Company A. """

        product_a = self.env['product.product'].create({
            'name': 'p1',
            'company_id': self.company_a.id,
        })
        mo = self.env['mrp.production'].create({
            'product_id': product_a.id,
            'product_uom_id': product_a.uom_id.id,
            'company_id': self.company_b.id,
        })
        with self.assertRaises(UserError):
            mo.action_confirm()

    def test_production_2(self):
        """Check that confirming a production in company b with user_a will create
        stock moves on company b. """

        product_a = self.env['product.product'].create({
            'name': 'p1',
            'company_id': self.company_a.id,
        })
        component_a = self.env['product.product'].create({
            'name': 'p2',
            'company_id': self.company_a.id,
        })
        self.env['mrp.bom'].create({
            'product_id': product_a.id,
            'product_tmpl_id': product_a.product_tmpl_id.id,
            'company_id': self.company_a.id,
            'bom_line_ids': [(0, 0, {'product_id': component_a.id})]
        })
        mo_form = Form(self.env['mrp.production'].with_user(self.user_a))
        mo_form.product_id = product_a
        mo = mo_form.save()
        mo.with_user(self.user_b).action_confirm()
        self.assertEqual(mo.move_raw_ids.company_id, self.company_a)
        self.assertEqual(mo.move_finished_ids.company_id, self.company_a)

    def test_product_produce_1(self):
        """Check that using a finished lot of company b in the produce wizard of a production
        of company a is not allowed """

        product = self.env['product.product'].create({
            'name': 'p1',
            'tracking': 'lot',
        })
        component = self.env['product.product'].create({
            'name': 'p2',
        })
        lot_b = self.env['stock.lot'].create({
            'product_id': product.id,
            'company_id': self.company_b.id,
        })
        self.env['mrp.bom'].create({
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'company_id': self.company_a.id,
            'bom_line_ids': [(0, 0, {'product_id': component.id})]
        })
        mo_form = Form(self.env['mrp.production'].with_user(self.user_a))
        mo_form.product_id = product
        # The mo must be confirmed, no longer in draft, in order for `lot_producing_id` to be visible in the view
        # <div class="o_row" invisible="state == 'draft' or product_tracking in ('none', False)">
        mo = mo_form.save()
        mo.action_confirm()
        mo_form = Form(mo)
        mo_form.lot_producing_id = lot_b
        mo = mo_form.save()
        with self.assertRaises(UserError):
            mo.with_user(self.user_b).action_confirm()

    def test_product_produce_2(self):
        """Check that using a component lot of company b in the produce wizard of a production
        of company a is not allowed """

        product = self.env['product.product'].create({
            'name': 'p1',
        })
        component = self.env['product.product'].create({
            'name': 'p2',
            'tracking': 'lot',
        })
        lot_b = self.env['stock.lot'].create({
            'product_id': component.id,
            'company_id': self.company_b.id,
        })
        self.env['mrp.bom'].create({
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'company_id': self.company_a.id,
            'bom_line_ids': [(0, 0, {'product_id': component.id})]
        })
        mo_form = Form(self.env['mrp.production'].with_user(self.user_a))
        mo_form.product_id = product
        mo = mo_form.save()
        mo.with_user(self.user_b).action_confirm()
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        details_operation_form = Form(mo.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = lot_b
            ml.quantity = 1
        details_operation_form.save()
        mo.move_raw_ids.picked = True
        with self.assertRaises(UserError):
            mo.button_mark_done()

    def test_is_kit_in_multi_company_env(self):
        """ Check that is_kits is company dependant """
        product1, product2 = self.env['product.product'].create([{'name': 'Kit Kat'}, {'name': 'twix'}])
        self.env['mrp.bom'].create([{
            'product_id': product1.id,
            'product_tmpl_id': product1.product_tmpl_id.id,
            'company_id': self.company_a.id,
            'type': 'phantom',
        }, {
            'product_id': product2.id,
            'product_tmpl_id': product2.product_tmpl_id.id,
            'company_id': False,
            'type': 'phantom',
        }])
        template1 = product1.product_tmpl_id
        template2 = product2.product_tmpl_id

        self.assertFalse(product1.with_context(allowed_company_ids=[self.company_b.id, self.company_a.id]).is_kits)
        self.assertFalse(template1.with_context(allowed_company_ids=[self.company_b.id, self.company_a.id]).is_kits)
        self.assertTrue(product1.with_company(self.company_a).is_kits)
        self.assertTrue(template1.with_company(self.company_a).is_kits)
        self.assertFalse(product1.with_company(self.company_b).is_kits)
        self.assertFalse(template1.with_company(self.company_b).is_kits)

        self.assertTrue(product2.with_company(self.company_a).is_kits)
        self.assertTrue(template2.with_company(self.company_a).is_kits)
        self.assertTrue(product2.with_company(self.company_b).is_kits)
        self.assertTrue(template2.with_company(self.company_b).is_kits)

    def test_partner_1(self):
        """ On a product without company, as a user of Company B, check it is not possible to use a
        location limited to Company A as `property_stock_production` """

        shared_product = self.env['product.product'].create({
            'name': 'Shared Product',
            'company_id': False,
        })
        with self.assertRaises(UserError):
            shared_product.with_user(self.user_b).property_stock_production = self.stock_location_a

    def test_company_specific_routes_and_company_creation(self):
        """
        Setup: company-specific manufacture routes
        Use case: create a new company
        A manufacture route should be created for the new company
        """
        company = self.env.company
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)

        manufacture_rule = warehouse.manufacture_pull_id
        manufacture_route = manufacture_rule.route_id

        # Allocate each company-specific manufacture rule to a new route
        for rule in manufacture_route.rule_ids.sudo():
            rule_company = rule.company_id
            if not rule_company or rule_company == company:
                continue
            manufacture_route.copy({
                'company_id': rule_company.id,
                'rule_ids': [(4, rule.id)],
            })
        # Also specify the company of the "generic route" (the one from the master data)
        manufacture_route.company_id = company

        new_company = self.env['res.company'].create({'name': 'Super Company'})
        new_warehouse = self.env['stock.warehouse'].search([('company_id', '=', new_company.id)], limit=1)
        self.assertEqual(new_warehouse.manufacture_pull_id.route_id.company_id, new_company)

    def test_company_specific_routes_and_warehouse_creation(self):
        """ Check that we are able to create a new warehouse when the generic manufacture route
        is in a different company. """
        group_stock_manager = self.env.ref('stock.group_stock_manager')
        self.user_a.write({'groups_id': [(4, group_stock_manager.id)]})

        manufacture_route = self.env.ref('mrp.route_warehouse0_manufacture')
        for rule in manufacture_route.rule_ids.sudo():
            rule_company = rule.company_id
            if not rule_company or rule_company == self.company_a:
                continue
            manufacture_route.copy({
                'company_id': rule_company.id,
                'rule_ids': [(4, rule.id)],
            })
        manufacture_route.company_id = self.company_a

        # Enable multi warehouse
        group_user = self.env.ref('base.group_user')
        group_stock_multi_warehouses = self.env.ref('stock.group_stock_multi_warehouses')
        group_stock_multi_locations = self.env.ref('stock.group_stock_multi_locations')
        self.env['res.config.settings'].create({
            'group_stock_multi_locations': True,
        }).execute()
        group_user.write({'implied_ids': [(4, group_stock_multi_warehouses.id), (4, group_stock_multi_locations.id)]})

        new_warehouse = self.env['stock.warehouse'].with_user(self.user_a).with_context(allowed_company_ids=[self.company_b.id]).create({
            'name': 'Warehouse #2',
            'code': 'WH2',
        })
        self.assertEqual(new_warehouse.manufacture_pull_id.route_id.company_id, self.company_b)

    def test_multi_company_kit_reservation(self):
        """
        Create and assign a delivery in company_b for a product that is a kit in company_a.
        Check that the move is treated just as a non-kit product.
        """
        """ Check that is_kits is company dependant """
        semi_kit_product = self.env['product.product'].create({
            'name': 'Kit Kat',
            'is_storable': True,
        })
        self.env['mrp.bom'].create([{
            'product_id': semi_kit_product.id,
            'product_tmpl_id': semi_kit_product.product_tmpl_id.id,
            'company_id': self.company_a.id,
            'type': 'phantom',
        }])
        warehouse_b = self.env['stock.warehouse'].search([('company_id', '=', self.company_b.id)], limit=1)
        delivery = self.env['stock.picking'].with_company(self.company_b.id).create({
            'picking_type_id': warehouse_b.out_type_id.id,
            'location_id': warehouse_b.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'move_ids': [Command.create({
                'name': semi_kit_product.name,
                'product_id': semi_kit_product.id,
                'product_uom_qty': 1,
                'location_id':  warehouse_b.lot_stock_id.id,
                'location_dest_id': self.ref('stock.stock_location_customers'),
            })]
        })
        # confirm and assign the delivery with company_a and check that it was treated as a non-kit product
        delivery.with_company(self.company_a).action_confirm()
        delivery.with_company(self.company_a).action_assign()
        self.assertRecordValues(delivery.move_ids, [{'state': 'confirmed', 'quantity': 0.0}])
