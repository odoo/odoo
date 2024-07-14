# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo import Command
from odoo.tests import Form
from odoo.addons.mrp_account.tests.test_analytic_account import TestMrpAnalyticAccount


class TestMrpAnalyticAccountHr(TestMrpAnalyticAccount):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.user_admin').groups_id += (
            cls.env.ref('analytic.group_analytic_accounting')
            + cls.env.ref('mrp.group_mrp_routings')
        )
        cls.workcenter.write({
            'employee_ids': [
                Command.create({
                    'name': 'Arthur Fu',
                    'pin': '1234',
                    'hourly_cost': 100,
                }),
                Command.create({
                    'name': 'Thomas Nific',
                    'pin': '5678',
                    'hourly_cost': 200,
                })
            ]
        })
        cls.employee1 = cls.env['hr.employee'].search([
            ('name', '=', 'Arthur Fu'),
        ])
        cls.employee2 = cls.env['hr.employee'].search([
            ('name', '=', 'Thomas Nific'),
        ])

    def test_mrp_employee_analytic_account(self):
        """Test when a wo requires employees, both aa lines for employees and for
        workcenters are correctly posted.
        """
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product
        mo_form.bom_id = self.bom
        mo_form.product_qty = 1.0
        mo_form.analytic_distribution = {str(self.analytic_account.id): 100.0}
        mo = mo_form.save()
        mo.action_confirm()
        with freeze_time('2027-10-01 10:00:00'):
            mo.workorder_ids.start_employee(self.employee1.id)
            mo.workorder_ids.start_employee(self.employee2.id)
            self.env.flush_all()   # need flush to trigger compute
        with freeze_time('2027-10-01 11:00:00'):
            mo.workorder_ids.stop_employee([self.employee1.id, self.employee2.id])
            self.env.flush_all()   # need flush to trigger compute
        employee1_aa_line = mo.workorder_ids.employee_analytic_account_line_ids.filtered(lambda l: l.employee_id == self.employee1)
        employee2_aa_line = mo.workorder_ids.employee_analytic_account_line_ids.filtered(lambda l: l.employee_id == self.employee2)
        self.assertEqual(employee1_aa_line.amount, -100.0)
        self.assertEqual(employee2_aa_line.amount, -200.0)
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_ids.amount, -10.0)
        self.assertEqual(employee1_aa_line[self.analytic_plan._column_name()], self.analytic_account)
        self.assertEqual(employee2_aa_line[self.analytic_plan._column_name()], self.analytic_account)
        new_account = self.env['account.analytic.account'].create({
            'name': 'test_analytic_account_change',
            'plan_id': self.analytic_plan.id,
        })
        mo.analytic_distribution = {str(new_account.id): 100.0}
        employee1_aa_line = mo.workorder_ids.employee_analytic_account_line_ids.filtered(lambda l: l.employee_id == self.employee1)
        employee2_aa_line = mo.workorder_ids.employee_analytic_account_line_ids.filtered(lambda l: l.employee_id == self.employee2)
        self.assertEqual(employee2_aa_line[self.analytic_plan._column_name()], new_account)
        self.assertEqual(employee1_aa_line[self.analytic_plan._column_name()], new_account)

    def test_mrp_analytic_account_without_workorder(self):
        """
        Test adding an analytic account to a confirmed manufacturing order without a work order.
        """
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
        })
        component = self.env['product.product'].create({
            'name': 'Test  Component',
            'type': 'product',
        })
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product
        mo_form.product_qty = 1.0
        with mo_form.move_raw_ids.new() as move:
            move.product_id = component
            move.product_uom_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')

        mo.analytic_distribution = {str(self.analytic_account.id): 100.0}
        self.assertEqual(mo.analytic_account_ids, self.analytic_account)

        mo_form = Form(mo)
        mo_form.qty_producing = 1.0
        mo = mo_form.save()
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')

    def test_mrp_analytic_account_with_workorder(self):
        """
        Test adding an analytic account to a confirmed manufacturing order with work orders.
        """
        # add a workorder to the BoM
        with self.with_user(self.env.ref('base.user_admin').login):
            self.workcenter.employee_ids = [Command.clear()]
            self.bom.write({
                'operation_ids': [(0, 0, {
                        'name': 'Test Operation 2',
                        'workcenter_id': self.workcenter.id,
                        'time_cycle': 60,
                    })
                ]
            })
            mo_form = Form(self.env['mrp.production'])
            mo_form.product_id = self.product
            mo_form.bom_id = self.bom
            mo_form.product_qty = 1.0
            mo = mo_form.save()
            mo.action_confirm()
            self.assertEqual(mo.state, 'confirmed')

            # start the workorders
            mo.workorder_ids[0].button_start()
            mo.workorder_ids[1].button_start()
            self.assertEqual(mo.workorder_ids[0].state, 'progress')
            self.assertTrue(mo.workorder_ids[0].time_ids)
            self.assertEqual(mo.workorder_ids[1].state, 'progress')
            self.assertTrue(mo.workorder_ids[1].time_ids)

            mo.analytic_distribution = {str(self.analytic_account.id): 100.0}
            self.assertEqual(mo.analytic_account_ids, self.analytic_account)

            mo_form = Form(mo)
            mo_form.qty_producing = 1.0
            mo = mo_form.save()
            mo.move_raw_ids.picked = True
            mo.button_mark_done()
            self.assertEqual(mo.state, 'done')

    def test_mrp_analytic_account_employee(self):
        """
            Test adding a user time to a work order.
        """
        user = self.env['res.users'].create({
            'name': 'Marc Demo',
            'email': 'mark.brown23@example.com',
            'image_1920': False,
            'login': 'demo_1',
            'password': 'demo_123'
        })
        self.env['hr.employee'].create({
            'user_id': user.id,
            'image_1920': False,
            'hourly_cost': 15,
        })
        workcenter = self.env['mrp.workcenter'].create({
            'name': 'Workcenter',
            'default_capacity': 1,
            'time_efficiency': 100,
            'costs_hour': 10,
        })
        # add a workorder to the BoM
        self.bom.write({
            'operation_ids': [(0, 0, {
                    'name': 'Test Operation 2',
                    'workcenter_id': workcenter.id,
                    'time_cycle': 60,
                })
            ]
        })
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product
        mo_form.bom_id = self.bom
        mo_form.product_qty = 1.0
        mo_form.analytic_distribution = {str(self.analytic_account.id): 100.0}
        mo = mo_form.save()
        # mo.analytic_distribution = {str(self.analytic_account.id): 100.0},
        # mo.analytic_account_id = self.analytic_account
        mo.action_confirm()
        time = self.env['mrp.workcenter.productivity'].create({
            'workcenter_id': workcenter.id,
            'date_start': datetime.now() - timedelta(minutes=30),
            'date_end': datetime.now(),
            'loss_id': self.env.ref('mrp.block_reason7').id,
            'workorder_id': mo.workorder_ids[1].id,
            'user_id': user.id,
        })
        mo_form = Form(mo)
        mo_form.qty_producing = 1.0
        mo = mo_form.save()
        mo.button_mark_done()
        self.assertEqual(len(self.analytic_account.with_context(analytic_plan_id=self.analytic_account.plan_id.id).line_ids), 4, '2 lines for workcenters costs 2 for employee cost')

        # delete a time from a workorder
        time.unlink()
        self.assertEqual(self.analytic_account.balance, -32.5, '-40 + 7.5 (30 mins worker time)')
        self.assertEqual(mo.workorder_ids[1].duration, 0, 'no time left on workorder')
