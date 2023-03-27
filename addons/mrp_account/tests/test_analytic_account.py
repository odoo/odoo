# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tests import Form


class TestMrpAnalyticAccount(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.write({'groups_id': [(4, cls.env.ref('analytic.group_analytic_accounting').id),]})

        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Plan',
            'company_id': False,
        })
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'test_analytic_account',
            'plan_id': cls.analytic_plan.id,
        })
        cls.workcenter = cls.env['mrp.workcenter'].create({
            'name': 'Workcenter',
            'default_capacity': 1,
            'time_efficiency': 100,
            'costs_hour': 10,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Product',
            'type': 'product',
            'standard_price': 233.0,
        })
        cls.component = cls.env['product.product'].create({
            'name': 'Component',
            'type': 'product',
            'standard_price': 10.0,
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_id': cls.product.id,
            'product_tmpl_id': cls.product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.component.id, 'product_qty': 1.0}),
            ],
            'operation_ids': [
                (0, 0, {'name': 'work work', 'workcenter_id': cls.workcenter.id, 'time_cycle': 15, 'sequence': 1}),
            ]})


class TestAnalyticAccount(TestMrpAnalyticAccount):
    def test_mo_analytic(self):
        """Test the amount on analytic line will change when consumed qty of the
        component changed.
        """
        # create a mo
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product
        mo_form.bom_id = self.bom
        mo_form.product_qty = 10.0
        mo_form.analytic_account_id = self.analytic_account
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(len(mo.move_raw_ids.analytic_account_line_id), 0)
        # increase qty_producing to 5.0
        mo_form = Form(mo)
        mo_form.qty_producing = 5.0
        mo_form.save()
        self.assertEqual(mo.state, 'progress')
        self.assertEqual(mo.move_raw_ids.analytic_account_line_id.amount, -50.0)

        # increase qty_producing to 10.0
        mo_form = Form(mo)
        mo_form.qty_producing = 10.0
        mo_form.save()
        # Hack to bypass test doing strange things
        mo._set_qty_producing()
        mo.workorder_ids.button_finish()
        self.assertEqual(mo.state, 'to_close')
        self.assertEqual(mo.move_raw_ids.analytic_account_line_id.amount, -100.0)

        # mark as done
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.move_raw_ids.analytic_account_line_id.amount, -100.0)

    def test_mo_analytic_backorder(self):
        """Test the analytic lines are correctly posted when backorder.
        """
        # create a mo
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product
        mo_form.bom_id = self.bom
        mo_form.product_qty = 10.0
        mo_form.analytic_account_id = self.analytic_account
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(len(mo.move_raw_ids.analytic_account_line_id), 0)

        # increase qty_producing to 5.0
        mo_form = Form(mo)
        mo_form.qty_producing = 5.0
        mo_form.save()
        self.assertEqual(mo.state, 'progress')
        self.assertEqual(mo.move_raw_ids.analytic_account_line_id.amount, -50.0)

        backorder_wizard_dict = mo.button_mark_done()
        Form(self.env[(backorder_wizard_dict.get('res_model'))].with_context(backorder_wizard_dict['context'])).save().action_backorder()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.move_raw_ids.analytic_account_line_id.amount, -50.0)

    def test_workcenter_same_analytic_account(self):
        """Test when workcenter and MO are using the same analytic account, no
        duplicated lines will be post.
        """
        # Required for `workorder_ids` to be visible in the view
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_routings')
        # set wc analytic account to be the same of the one on the bom
        self.workcenter.costs_hour_account_id = self.analytic_account

        # create a mo
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product
        mo_form.bom_id = self.bom
        mo_form.product_qty = 10.0
        mo_form.analytic_account_id = self.analytic_account
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(len(mo.workorder_ids.wc_analytic_account_line_id), 0)

        # change duration to 60
        mo_form = Form(mo)
        with mo_form.workorder_ids.edit(0) as line_edit:
            line_edit.duration = 60.0
        mo_form.save()
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_id.amount, -10.0)
        self.assertEqual(len(mo.workorder_ids.wc_analytic_account_line_id), 0)

        # change duration to 120
        with mo_form.workorder_ids.edit(0) as line_edit:
            line_edit.duration = 120.0
        mo_form.save()
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_id.amount, -20.0)
        self.assertEqual(len(mo.workorder_ids.wc_analytic_account_line_id), 0)

        # mark as done
        mo_form.qty_producing = 10.0
        mo_form.save()
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_id.amount, -20.0)
        self.assertEqual(len(mo.workorder_ids.wc_analytic_account_line_id), 0)

    def test_workcenter_different_analytic_account(self):
        """Test when workcenter and MO are using the same analytic account, no
        duplicated lines will be post.
        """
        # Required for `workorder_ids` to be visible in the view
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_routings')
        # set wc analytic account to be different from the one on the bom
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test', 'company_id': False})
        wc_analytic_account = self.env['account.analytic.account'].create({'name': 'wc_analytic_account', 'plan_id': analytic_plan.id})
        self.workcenter.costs_hour_account_id = wc_analytic_account

        # create a mo
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product
        mo_form.bom_id = self.bom
        mo_form.product_qty = 10.0
        mo_form.analytic_account_id = self.analytic_account
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(len(mo.workorder_ids.wc_analytic_account_line_id), 0)

        # change duration to 60
        mo_form = Form(mo)
        with mo_form.workorder_ids.edit(0) as line_edit:
            line_edit.duration = 60.0
        mo_form.save()
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_id.amount, -10.0)
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_id.account_id, self.analytic_account)
        self.assertEqual(mo.workorder_ids.wc_analytic_account_line_id.amount, -10.0)
        self.assertEqual(mo.workorder_ids.wc_analytic_account_line_id.account_id, wc_analytic_account)

        # change duration to 120
        with mo_form.workorder_ids.edit(0) as line_edit:
            line_edit.duration = 120.0
        mo_form.save()
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_id.amount, -20.0)
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_id.account_id, self.analytic_account)
        self.assertEqual(mo.workorder_ids.wc_analytic_account_line_id.amount, -20.0)
        self.assertEqual(mo.workorder_ids.wc_analytic_account_line_id.account_id, wc_analytic_account)

        # mark as done
        mo_form.qty_producing = 10.0
        mo_form.save()
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_id.amount, -20.0)
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_id.account_id, self.analytic_account)
        self.assertEqual(mo.workorder_ids.wc_analytic_account_line_id.amount, -20.0)
        self.assertEqual(mo.workorder_ids.wc_analytic_account_line_id.account_id, wc_analytic_account)

    def test_changing_mo_analytic_account(self):
        """ Check if the MO account analytic lines are correctly updated
            after the change of the MO account analytic.
        """
        # create a mo
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product
        mo_form.bom_id = self.bom
        mo_form.product_qty = 1
        mo_form.analytic_account_id = self.analytic_account
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(len(mo.move_raw_ids.analytic_account_line_id), 0)

        # Mark as done
        wizard_dict = mo.button_mark_done()
        Form(self.env[(wizard_dict.get('res_model'))].with_context(wizard_dict['context'])).save().process()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(len(mo.move_raw_ids.analytic_account_line_id), 1)

        # Create a new analytic account
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test', 'company_id': False})
        new_analytic_account = self.env['account.analytic.account'].create({'name': 'test_analytic_account_2', 'plan_id': analytic_plan.id})
        # Change the MO analytic account
        mo.analytic_account_id = new_analytic_account
        self.assertEqual(mo.move_raw_ids.analytic_account_line_id.account_id.id, new_analytic_account.id)

        #Get the MO analytic account lines
        mo_analytic_account_lines = mo.move_raw_ids.analytic_account_line_id
        mo.analytic_account_id = False
        # Check that the MO analytic account lines are deleted
        self.assertEqual(len(mo.move_raw_ids.analytic_account_line_id), 0)
        self.assertFalse(mo_analytic_account_lines.exists())
        # Check that the AA lines are recreated correctly if we delete the AA, save the MO, and assign a new one
        mo.analytic_account_id = self.analytic_account
        self.assertEqual(len(mo.move_raw_ids.analytic_account_line_id), 1)

    def test_add_wo_analytic_no_company(self):
        """Test the addition of work orders to a MO linked to
        an analytic account that has no company associated
        """
        # Create an analytic account and remove the company
        analytic_account_no_company = self.env['account.analytic.account'].create({
            'name': 'test_analytic_account_no_company',
            'plan_id': self.analytic_plan.id,
        })
        analytic_account_no_company.company_id = False

        # Create a mo linked to an analytic account with no associated company
        mo_no_company = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'analytic_account_id': analytic_account_no_company.id,
            'product_uom_id': self.bom.product_uom_id.id,
        })

        mo_no_c_form = Form(mo_no_company)
        self.env['mrp.workorder'].create({
            'name': 'Work_order',
            'workcenter_id': self.workcenter.id,
            'product_uom_id': self.bom.product_uom_id.id,
            'production_id': mo_no_c_form.id,
        })
        mo_no_c_form.save()
        self.assertTrue(mo_no_company.workorder_ids)
