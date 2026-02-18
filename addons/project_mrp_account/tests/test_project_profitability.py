# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from odoo.addons.project.tests.test_project_profitability import TestProjectProfitabilityCommon


@tagged('-at_install', 'post_install')
class TestSaleProjectProfitabilityMrp(TestProjectProfitabilityCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.foreign_company = cls.env['res.company'].create(
            {'name': "My Test Company", 'currency_id': cls.foreign_currency.id})

    def test_profitability_mrp_project(self):
        """ This test ensures that when mrp are linked to the project, the total is correctly computed for the project profitability. """

        project = self.env['project.project'].create({'name': 'new project'})
        project._create_analytic_account()
        account = project.account_id
        # creates the aal for the project
        self.env['account.analytic.line'].create([{
            'name': 'line 1',
            'account_id': account.id,
            'category': 'manufacturing_order',
            'company_id': self.foreign_company.id,
            'amount': '500',
            'unit_amount': '1',
        }, {
            'name': 'line 2',
            'account_id': account.id,
            'category': 'manufacturing_order',
            'company_id': self.foreign_company.id,
            'amount': '100',
            'unit_amount': '1',
        }])
        # Ensures that if none of the mrp linked to the project have the same company as the current active company, the total is still converted into the current active company.
        self.assertDictEqual(project._get_profitability_items(with_action=False), {
            'revenues': {'data': [], 'total': {'invoiced': 0.0, 'to_invoice': 0.0}},
            'costs': {'data': [{'id': 'manufacturing_order', 'sequence': 12, 'billed': 120.0, 'to_bill': 0.0}], 'total': {'billed': 120.0, 'to_bill': 0.0}}
        })
        self.env['account.analytic.line'].create([{
            'name': 'line 3',
            'account_id': account.id,
            'category': 'manufacturing_order',
            'company_id': self.env.company.id,
            'amount': '500',
            'unit_amount': '1',
        }, {
            'name': 'line 4',
            'account_id': account.id,
            'category': 'manufacturing_order',
            'company_id': self.env.company.id,
            'amount': '200',
            'unit_amount': '1',
        }])
        # Adds mrp AAL with the default company
        self.assertDictEqual(project._get_profitability_items(with_action=False), {
                'revenues': {'data': [], 'total': {'invoiced': 0.0, 'to_invoice': 0.0}},
                'costs': {'data': [{'id': 'manufacturing_order', 'sequence': 12, 'billed': 820.0, 'to_bill': 0.0}], 'total': {'billed': 820.0, 'to_bill': 0.0}}
        })

    def test_profitability_for_multi_level_mo(self):
        """
            This test creates a 2-level manufacturing hierarchy:
                - Main Product -> BoM:
                    - Component -> BoM:
                        - Raw Material
            Routes are set up as follows:
            - (Main Product + Component) have the routes 'Make To Order' + 'Manufacture'.
            - (Raw Material) has the route 'Buy'.
            The test's main goal is to verify that the project's profitability calculation correctly includes ONLY
            the parent MO's cost, ignoring the child MO's cost to prevent double-counting.
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        mto_route = warehouse.mto_pull_id.route_id
        manufacture_route = warehouse.manufacture_pull_id.route_id
        mto_route.active = True
        buy_route = self.env['stock.route'].search([('name', '=', 'Buy')])
        project = self.env['project.project'].create({'name': 'new project for mo source'})
        project._create_analytic_account()

        main_product, component = self.env['product.product'].create([{
            'name': product_name,
            'is_storable': True,
            'route_ids': [Command.set([mto_route.id, manufacture_route.id])],
        } for product_name in ['main_product', 'component']])
        raw_material = self.env['product.product'].create({
            'name': 'raw_material',
            'type': 'consu',
            'route_ids': [Command.set([buy_route.id])],
        })

        # Manually creating BoMs for our products to set up the hierarchy.
        main_product_bom = self.env['mrp.bom'].create([
            {
                'product_tmpl_id': main_product.product_tmpl_id.id,
                'product_qty': 1,
                'bom_line_ids': [
                    Command.create({
                        'product_id': component.id,
                        'product_qty': 1
                    }),
                ],
            },
        ])
        component_bom = self.env['mrp.bom'].create([
            {
                'product_tmpl_id': component.product_tmpl_id.id,
                'product_qty': 1,
                'bom_line_ids': [
                    Command.create({
                        'product_id': raw_material.id,
                        'product_qty': 1
                    }),
                ],
            },
        ])

        # Create and confirm the main MO, which should trigger the creation of the component MO
        main_mo = self.env["mrp.production"].create({'product_id': main_product.id, 'bom_id': main_product_bom.id, 'project_id': project.id})
        main_mo.action_confirm()
        component_mo = self.env['mrp.production'].search([('product_id', '=', component.id), ('project_id', '=', project.id)], order='id DESC', limit=1)

        self.assertTrue(component_mo, "Child MO for Component was not created.")
        self.assertEqual(component_mo.bom_id, component_bom, "Child MO BoM Id should equal to the component's BoM.")
        self.assertEqual(component_mo._get_sources(), main_mo, "Component MO's source should be main MO.")

        # Parent MO analytic line
        parent_aal = self.env["account.analytic.line"].create([{
            "name": main_mo.name,
            "account_id": project.account_id.id,
            "category": "manufacturing_order",
            "company_id": self.env.company.id,
            "amount": 150.0,
            "unit_amount": 1.0,
        }])
        # Child MO analytic line
        child_aal = self.env["account.analytic.line"].create([{
            "name": component_mo.name,
            "account_id": project.account_id.id,
            "category": "manufacturing_order",
            "company_id": self.env.company.id,
            "amount": 100.0,
            "unit_amount": 1.0,
        }])

        # Associate parent and child AALs with their respective stock moves
        main_mo_moves = main_mo.move_finished_ids | main_mo.move_raw_ids
        component_mo_moves = component_mo.move_finished_ids | component_mo.move_raw_ids

        main_mo_moves.write({"analytic_account_line_ids": [Command.link(parent_aal.id)]})
        component_mo_moves.write({"analytic_account_line_ids": [Command.link(child_aal.id)]})

        profitability_items = project._get_profitability_items(with_action=False)
        self.assertEqual(profitability_items["costs"]["total"]["billed"], 150.0,
            "Profitability total should reflect only the parent MO cost.",
        )
