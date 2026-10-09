# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.sale_mrp.tests.test_multistep_manufacturing import TestMultistepManufacturing
from odoo.tests import common, Form


@common.tagged('post_install', '-at_install')
class TestSaleMrpAccount(TestMultistepManufacturing):

    # A manufacturing order triggered by a sales order posts its costs on the
    # analytic account of the project.
    _test_user_groups = (
        'mrp.group_mrp_manager',  # FIXME: use mrp.group_mrp_user
        'mrp.group_mrp_routings',  # view visibility (workorder fields)
        'stock.group_stock_manager',  # FIXME: use stock.group_stock_user
        'sales_team.group_sale_manager',  # FIXME: use sales_team.group_sale_salesman
        'account.group_account_manager',  # FIXME: use account.group_account_invoice
        'product.group_product_manager',  # FIXME: use base.group_user
        'uom.group_uom',  # view visibility (uom_id)
        'project.group_project_manager',  # FIXME: use project.group_project_user
        'analytic.group_analytic_accounting',  # view visibility (analytic_distribution)
    )

    _test_user_name = 'Test Project Manufacturing Manager'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_plan, _other_plans = cls.env['account.analytic.plan']._get_all_plans()
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'test_analytic_account',
            'plan_id': cls.project_plan.id,
        })
        cls.workcenter = cls.env['mrp.workcenter'].create({
            'name': 'Workcenter',
            'time_efficiency': 100,
            'costs_hour': 10,
        })
        cls.product, cls.component = cls.env['product.product'].create([{
            'name': 'Product',
            'is_storable': True,
            'standard_price': 233.0,
        }, {
            'name': 'Component',
            'is_storable': True,
            'standard_price': 10.0,
        }])
        cls.bom = cls.env['mrp.bom'].create({
            'product_id': cls.product.id,
            'product_tmpl_id': cls.product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                Command.create({'product_id': cls.component.id, 'product_qty': 1.0}),
            ],
            'operation_ids': [
                Command.create({'name': 'work work', 'workcenter_id': cls.workcenter.id, 'time_cycle': 15, 'sequence': 1}),
            ]
        })
        cls.project = cls.env['project.project'].create({
            'name': 'Test Projet',
            'account_id': cls.analytic_account.id,
        })

    def test_analytic_line_billable_type_mrp(self):
        """ This test ensures that when a project is set on a manufacturing order, the aal's generated have the correct
        'manufacturing order' billable_type and category_report """

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product
        mo_form.bom_id = self.bom
        mo_form.product_qty = 1
        mo_form.project_id = self.project
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_mark_done()
        self.assertEqual(mo.move_raw_ids.analytic_account_line_ids.category_report, 'costs')
        self.assertEqual(mo.move_raw_ids.analytic_account_line_ids.billable_type, '14_manufacturing_order')

    def test_mo_get_project_from_so(self):
        """ ensure the project of MO is inherited from the SO if no project is set """
        self.sale_order.project_id = self.project
        self.assertFalse(self.sale_order.mrp_production_ids.project_id)
        self.sale_order.action_confirm()
        self.assertEqual(self.sale_order.mrp_production_ids.project_id, self.project)
