# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tests import Form


class TestAnalyticAccount(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.write({'groups_id': [(4, cls.env.ref('analytic.group_analytic_accounting').id),]})

        cls.analytic_account = cls.env['account.analytic.account'].create({'name': 'test_analytic_account'})
        cls.workcenter = cls.env['mrp.workcenter'].create({
            'name': 'Workcenter',
            'capacity': 1,
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
        # set wc analytic account to be different from the one on the bom
        wc_analytic_account = self.env['account.analytic.account'].create({'name': 'wc_analytic_account'})
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
