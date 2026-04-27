# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, Form
from freezegun import freeze_time
from odoo import Command

from odoo.addons.project.tests.test_project_profitability import TestProjectProfitabilityCommon


@tagged('-at_install', 'post_install')
class TestProjectProfitabilityMrpEmployee(TestProjectProfitabilityCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Both groups below are required to make fields `product_uom_id` and
        # `workorder_ids' visible in the view of `mrp.production`. The
        # subviews of`workorder_ids` must be present in the test to create records.
        cls.env.user.groups_id += cls.env.ref('uom.group_uom') + cls.env.ref('mrp.group_mrp_routings')

        cls.user = cls.env['res.users'].create([{
            'name': 'Chris Wilson',
            'email': 'chris.wilson23@example.com',
            'image_1920': False,
            'login': 'weight_1',
            'password': 'weight_123'
        }])
        cls.employee_ggg = cls.env['hr.employee'].create([{
            'user_id': cls.user.id,
            'image_1920': False,
            'hourly_cost': 150,
        }])
        cls.workcenter = cls.env['mrp.workcenter'].create([{
            'name': 'Workcenter',
            'default_capacity': 1,
            'time_efficiency': 100,
            'costs_hour': 30,
        }])
        cls.product_produced = cls.env['product.product'].create([{
            'name': 'Product',
            'is_storable': True,
            'standard_price': 233.0,
        }])
        cls.component = cls.env['product.product'].create([{
            'name': 'Component',
            'is_storable': True,
            'standard_price': 5.0,
        }])
        cls.bom = cls.env['mrp.bom'].create([{
            'product_id': cls.product_produced.id,
            'product_tmpl_id': cls.product_produced.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                Command.create({
                    'product_id': cls.component.id,
                    'product_qty': 5.0
                }),
            ],
            'operation_ids': [
                Command.create({
                    'name': 'work work',
                    'workcenter_id': cls.workcenter.id,
                    'time_cycle': 60, 'sequence': 1
                }),
            ]
        }])

    def test_profitability_mrp_employee_project(self):
        """
        This test ensures that when hr.employee, project & mrp are installed, the section 'manufacturing order' of the
        project profitability is correctly computed.
        The expected content of this section is the following value :
        - the total cost of the product consumed by the MO
        - the total wage of the employee working on the work center
        - the total cost of the work center
        """
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_produced
        mo_form.bom_id = self.bom
        mo_form.product_qty = 1.0
        mo_form.project_id = self.project
        mo = mo_form.save()
        with freeze_time('2027-10-01 10:00:00'):
            mo.workorder_ids.start_employee(self.employee_ggg.id)
            self.env.flush_all()   # need flush to trigger compute
        with freeze_time('2027-10-01 11:00:00'):
            mo.workorder_ids.stop_employee([self.employee_ggg.id])
            self.env.flush_all()   # need flush to trigger compute
        mo.action_confirm()
        mo.button_mark_done()

        # The expected total is 30 + 150 + 5*5 ( work center costs - employee cost - products consumed)
        self.assertEqual(self.project._get_profitability_items(False)['costs']['data'],
                         [{'id': 'manufacturing_order', 'sequence': 12, 'billed': -205.0, 'to_bill': 0.0}])
