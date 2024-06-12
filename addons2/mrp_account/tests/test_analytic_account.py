# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tests import Form


class TestMrpAnalyticAccount(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The group 'mrp.group_mrp_routings' is required to make the field
        # 'workorder_ids' visible in the view of 'mrp.production'. The subviews
        #  of `workorder_ids` must be present in many tests to create records.
        cls.env.user.groups_id += (
            cls.env.ref('analytic.group_analytic_accounting')
            + cls.env.ref('mrp.group_mrp_routings')
        )

        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Plan',
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
        mo_form.analytic_distribution = {str(self.analytic_account.id): 100.0}
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(len(mo.move_raw_ids.analytic_account_line_ids), 0)
        # increase qty_producing to 5.0
        mo_form = Form(mo)
        mo_form.qty_producing = 5.0
        mo_form.save()
        self.assertEqual(mo.state, 'progress')
        self.assertEqual(mo.move_raw_ids.analytic_account_line_ids.amount, -50.0)

        # increase qty_producing to 10.0
        mo_form = Form(mo)
        mo_form.qty_producing = 10.0
        mo_form.save()
        mo.workorder_ids.button_finish()
        self.assertEqual(mo.state, 'to_close')
        self.assertEqual(mo.move_raw_ids.analytic_account_line_ids.amount, -100.0)

        # mark as done
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.move_raw_ids.analytic_account_line_ids.amount, -100.0)

    def test_mo_analytic_backorder(self):
        """Test the analytic lines are correctly posted when backorder.
        """
        # create a mo
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product
        mo_form.bom_id = self.bom
        mo_form.product_qty = 10.0
        mo_form.analytic_distribution = {str(self.analytic_account.id): 100.0}
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(len(mo.move_raw_ids.analytic_account_line_ids), 0)

        # increase qty_producing to 5.0
        mo_form = Form(mo)
        mo_form.qty_producing = 5.0
        mo_form.save()
        self.assertEqual(mo.state, 'progress')
        self.assertEqual(mo.move_raw_ids.analytic_account_line_ids.amount, -50.0)

        backorder_wizard_dict = mo.button_mark_done()
        Form(self.env[(backorder_wizard_dict.get('res_model'))].with_context(backorder_wizard_dict['context'])).save().action_backorder()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.move_raw_ids.analytic_account_line_ids.amount, -50.0)

    def test_workcenter_different_analytic_account(self):
        """Test when workcenter and MO are using the same analytic account, no
        duplicated lines will be post.
        """
        # Required for `workorder_ids` to be visible in the view
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_routings')
        # set wc analytic account to be different from the one on the bom
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test'})
        wc_analytic_account = self.env['account.analytic.account'].create({'name': 'wc_analytic_account', 'plan_id': analytic_plan.id})
        self.workcenter.analytic_distribution = {str(wc_analytic_account.id): 100.0}

        # create a mo
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product
        mo_form.bom_id = self.bom
        mo_form.product_qty = 10.0
        mo_form.analytic_distribution = {str(self.analytic_account.id): 100.0}
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(len(mo.workorder_ids.wc_analytic_account_line_ids), 0)

        # change duration to 60
        mo_form = Form(mo)
        with mo_form.workorder_ids.edit(0) as line_edit:
            line_edit.duration = 60.0
        mo_form.save()
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_ids.amount, -10.0)
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_ids[self.analytic_plan._column_name()], self.analytic_account)
        self.assertEqual(mo.workorder_ids.wc_analytic_account_line_ids.amount, -10.0)
        self.assertEqual(mo.workorder_ids.wc_analytic_account_line_ids[analytic_plan._column_name()], wc_analytic_account)

        # change duration to 120
        with mo_form.workorder_ids.edit(0) as line_edit:
            line_edit.duration = 120.0
        mo_form.save()
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_ids.amount, -20.0)
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_ids[self.analytic_plan._column_name()], self.analytic_account)
        self.assertEqual(mo.workorder_ids.wc_analytic_account_line_ids.amount, -20.0)
        self.assertEqual(mo.workorder_ids.wc_analytic_account_line_ids[analytic_plan._column_name()], wc_analytic_account)

        # mark as done
        mo_form.qty_producing = 10.0
        mo_form.save()
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_ids.amount, -20.0)
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_ids[self.analytic_plan._column_name()], self.analytic_account)
        self.assertEqual(mo.workorder_ids.wc_analytic_account_line_ids.amount, -20.0)
        self.assertEqual(mo.workorder_ids.wc_analytic_account_line_ids[analytic_plan._column_name()], wc_analytic_account)

    def test_changing_mo_analytic_account(self):
        """ Check if the MO account analytic lines are correctly updated
            after the change of the MO account analytic.
        """
        # Required for `workorder_ids` to be visible in the view
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_routings')
        # create a mo
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product
        mo_form.bom_id = self.bom
        mo_form.product_qty = 1
        mo_form.analytic_distribution = {str(self.analytic_account.id): 100.0}
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(len(mo.move_raw_ids.analytic_account_line_ids), 0)
        self.assertEqual(len(mo.workorder_ids.mo_analytic_account_line_ids), 0)

        # Change duration to 60
        mo_form = Form(mo)
        with mo_form.workorder_ids.edit(0) as line_edit:
            line_edit.duration = 60.0
        mo_form.save()
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_ids[self.analytic_plan._column_name()], self.analytic_account)

        # Mark as done
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(len(mo.move_raw_ids.analytic_account_line_ids), 1)

        # Create a new analytic account
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test'})
        new_analytic_account = self.env['account.analytic.account'].create({'name': 'test_analytic_account_2', 'plan_id': analytic_plan.id})
        # Change the MO analytic account
        mo.analytic_distribution = {str(new_analytic_account.id): 100.0}
        self.assertEqual(mo.move_raw_ids.analytic_account_line_ids[analytic_plan._column_name()], new_analytic_account)
        self.assertEqual(mo.workorder_ids.mo_analytic_account_line_ids[analytic_plan._column_name()], new_analytic_account)

        #Get the MO analytic account lines
        mo_analytic_account_raw_lines = mo.move_raw_ids.analytic_account_line_ids
        mo_analytic_account_wc_lines = mo.move_raw_ids.analytic_account_line_ids
        mo.analytic_distribution = {}
        # Check that the MO analytic account lines are deleted
        self.assertEqual(len(mo.move_raw_ids.analytic_account_line_ids), 0)
        self.assertEqual(len(mo.workorder_ids.mo_analytic_account_line_ids), 0)
        self.assertFalse(mo_analytic_account_raw_lines.exists())
        self.assertFalse(mo_analytic_account_wc_lines.exists())
        # Check that the AA lines are recreated correctly if we delete the AA, save the MO, and assign a new one
        mo.analytic_distribution = {str(self.analytic_account.id): 100.0}
        self.assertEqual(len(mo.move_raw_ids.analytic_account_line_ids), 1)
        self.assertEqual(len(mo.workorder_ids.mo_analytic_account_line_ids), 1)

    def test_add_remove_wo_analytic_no_company(self):
        """Test the addition and removal of work orders to a MO linked to
        an analytic account that has no company associated
        """
        # Create an analytic account and remove the company
        analytic_account_no_company = self.env['account.analytic.account'].create({
            'name': 'test_analytic_account_no_company',
            'plan_id': self.analytic_plan.id,
        }).with_context(analytic_plan_id=self.analytic_plan.id)
        analytic_account_no_company.company_id = False

        # Create a mo linked to an analytic account with no associated company
        mo_no_company = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'analytic_distribution': {str(analytic_account_no_company.id): 100.0},
            'product_uom_id': self.bom.product_uom_id.id,
        })

        mo_no_c_form = Form(mo_no_company)
        wo = self.env['mrp.workorder'].create({
            'name': 'Work_order',
            'workcenter_id': self.workcenter.id,
            'product_uom_id': self.bom.product_uom_id.id,
            'production_id': mo_no_c_form.id,
            'duration': 60,
        })
        mo_no_c_form.save()
        self.assertTrue(mo_no_company.workorder_ids)
        self.assertEqual(wo.production_id.analytic_account_ids, analytic_account_no_company)
        self.assertEqual(len(analytic_account_no_company.line_ids), 1)
        mo_no_company.workorder_ids.unlink()
        self.assertEqual(len(analytic_account_no_company.line_ids), 0)

    def test_update_components_qty_to_0(self):
        """ Test that the analytic lines are deleted when the quantity of the component is set to 0.
            Create a Mo with analytic account and a component, confirm and validate it,
            set the quantity of the component to 0, the analytic lines should be deleted.
        """
        component = self.env['product.product'].create({
            'name': 'Component',
            'type': 'product',
            'standard_price': 100,
        })
        product = self.env['product.product'].create({
            'name': 'Product',
            'type': 'product',
        })
        bom = self.env['mrp.bom'].create({
                'product_tmpl_id': product.product_tmpl_id.id,
                'product_qty': 1,
                'product_uom_id': product.uom_id.id,
                'type': 'normal',
                'bom_line_ids': [(0, 0, {
                    'product_id': component.id,
                    'product_qty': 1,
                    'product_uom_id': component.uom_id.id,
                })],
        })
        analytic_account = self.env['account.analytic.account'].create({
            'name': "Test Account",
            'plan_id': self.analytic_plan.id,
        })
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product
        mo_form.bom_id = bom
        mo_form.product_qty = 1.0
        mo_form.analytic_distribution = {str(analytic_account.id): 100.0}
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')


        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        self.assertEqual(mo.state, 'to_close')
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(analytic_account.debit, 100)
        mo.move_raw_ids[0].quantity = 0
        self.assertEqual(analytic_account.debit, 0)
        self.assertFalse(analytic_account.line_ids)

    def test_cross_analytics(self):
        """ Test analytic distributions (AD) with cross analytics on an MO."""

        ap1 = self.env['account.analytic.plan'].create({
            'name': 'Plan 1',
        })
        ap2 = self.env['account.analytic.plan'].create({
            'name': 'Plan 2',
        })
        ac1A = self.env['account.analytic.account'].create({
            'name': 'test_cross_analytics plan 1 account A',
            'plan_id': ap1.id,
        })
        ac1B = self.env['account.analytic.account'].create({
            'name': 'test_cross_analytics plan 1 account B',
            'plan_id': ap1.id,
        })
        ac1C = self.env['account.analytic.account'].create({
            'name': 'test_cross_analytics plan 1 account C',
            'plan_id': ap1.id,
        })
        ac2A = self.env['account.analytic.account'].create({
            'name': 'test_cross_analytics plan 2 account A',
            'plan_id': ap2.id,
        })
        ac2B = self.env['account.analytic.account'].create({
            'name': 'test_cross_analytics plan 2 account B',
            'plan_id': ap2.id,
        })
        ac2C = self.env['account.analytic.account'].create({
            'name': 'test_cross_analytics plan 2 account C',
            'plan_id': ap2.id,
        })

        analytic_distribution = {
            f"{ac1A.id},{ac2A.id}": 33.33,
            f"{ac1B.id},{ac2B.id}": 33.33,
            f"{ac1C.id},{ac2C.id}": 33.33,
        }

        # create a mo
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product
        mo_form.bom_id = self.bom
        mo_form.product_qty = 10.0
        mo_form.analytic_distribution = analytic_distribution
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(len(mo.move_raw_ids.analytic_account_line_ids), 0)
        # increase qty_producing to 5.0
        mo_form = Form(mo)
        mo_form.qty_producing = 5.0
        mo_form.save()
        self.assertEqual(mo.state, 'progress')
        aals = mo.move_raw_ids.analytic_account_line_ids
        self.assertEqual(len(aals), 3)
        self.assertEqual(sum(aals.mapped('amount')), -49.99)

        # increase qty_producing to 10.0
        mo_form = Form(mo)
        mo_form.qty_producing = 10.0
        mo_form.save()
        mo.workorder_ids.button_finish()
        aals = mo.move_raw_ids.analytic_account_line_ids

        self.assertEqual(mo.state, 'to_close')
        self.assertEqual(len(aals), 3)
        self.assertEqual(sum(aals.mapped('amount')), -99.99)

        # mark as done
        mo.button_mark_done()
        aals = mo.move_raw_ids.analytic_account_line_ids
        self.assertEqual(mo.state, 'done')
        self.assertEqual(len(aals), 3)
        self.assertEqual(sum(aals.mapped('amount')), -99.99)

        # assert the right accounts are on the right analytic lines
        ap1_column = ap1._column_name()
        ap2_column = ap2._column_name()
        line_with_A_accounts = aals.filtered_domain([(ap1_column, '=', ac1A.id)])
        line_with_B_accounts = aals.filtered_domain([(ap1_column, '=', ac1B.id)])
        line_with_C_accounts = aals.filtered_domain([(ap1_column, '=', ac1C.id)])
        self.assertEqual(line_with_A_accounts[ap2_column], ac2A)
        self.assertEqual(line_with_B_accounts[ap2_column], ac2B)
        self.assertEqual(line_with_C_accounts[ap2_column], ac2C)

        # ensure the right amounts are on the right lines
        # the distribution calculation corrects for rounding error accumulation to ensure
        # the total sum is correct, so individual lines can have minor deviations
        self.assertAlmostEqual(line_with_A_accounts.amount, -100/3, delta=0.02)
        self.assertAlmostEqual(line_with_B_accounts.amount, -100/3, delta=0.02)
        self.assertAlmostEqual(line_with_B_accounts.amount, -100/3, delta=0.02)

    def test_mo_qty_analytics(self):
        """
        This test tests multiple behaviours and edge cases. First off, when
        an analytic distribution with an MO, the analytic entries should only
        be generated when the MO's components are consumed/reserved (i.e.
        picked). Second, when changing the produced quantity in a confirmed MO,
        it should appropriately adjust the amount of picked components. Third,
        analytic entries should at all times reflect the current situation, and
        thus must be regenerated every time there's a change in components'
        picked status.
        """
        # refill components
        location = self.env.ref('stock.stock_location_stock')
        self.env['stock.quant']._update_available_quantity(self.component, location, 10)

        # create a mo
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product
        mo_form.bom_id = self.bom
        mo_form.product_qty = 10.0
        mo_form.analytic_distribution = {str(self.analytic_account.id): 100.0}
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(self.analytic_account.balance, 0.0)

        # increase qty_producing to 5.0
        mo_form = Form(mo)
        mo_form.qty_producing = 5.0
        mo_form.save()
        self.assertEqual(mo.state, 'progress')
        self.assertEqual(self.analytic_account.balance, -50.0)

        # decrease qty_producing to 0.0
        mo_form = Form(mo)
        mo_form.qty_producing = 0.0
        mo_form.save()
        self.assertEqual(mo.state, 'progress')
        self.assertEqual(self.analytic_account.balance, 0.0)
