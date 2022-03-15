# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo.addons.sale_timesheet.tests.common_reporting import TestCommonReporting
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestReporting(TestCommonReporting):

    def test_profitability_report(self):

        # this test suppose everything is in the same currency as the current one
        currency = self.env.company.currency_id
        rounding = currency.rounding

        project_global_stat = self.env['project.profitability.report'].search([('project_id', '=', self.project_global.id)]).read()[0]
        self.assertTrue(float_is_zero(project_global_stat['amount_untaxed_invoiced'], precision_rounding=rounding), "The invoiced amount of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['amount_untaxed_to_invoice'], precision_rounding=rounding), "The amount to invoice of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['timesheet_unit_amount'], precision_rounding=rounding), "The timesheet unit amount of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['timesheet_cost'], precision_rounding=rounding), "The timesheet cost of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the global project should be 0.0")

        # confirm sales orders
        self.sale_order_1.action_confirm()
        self.sale_order_2.action_confirm()
        self.sale_order_3.action_confirm()
        self.env['project.profitability.report'].flush()

        project_so_1 = self.so_line_deliver_project.project_id
        project_so_2 = self.so_line_order_project.project_id
        project_so_3 = self.so_line_deliver_manual_project.project_id

        task_so_1 = self.so_line_deliver_project.task_id
        task_so_2 = self.so_line_order_project.task_id
        task_so_3 = self.so_line_deliver_manual_project.task_id

        task_in_global_1 = self.so_line_deliver_task.task_id
        task_in_global_2 = self.so_line_order_task.task_id

        # deliver project should not be impacted, as no timesheet are logged yet
        project_so_1_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_1.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        self.assertTrue(float_is_zero(project_so_1_stat['amount_untaxed_invoiced'], precision_rounding=rounding), "The invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['amount_untaxed_to_invoice'], precision_rounding=rounding), "The amount to invoice of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['timesheet_unit_amount'], precision_rounding=rounding), "The timesheet unit amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['timesheet_cost'], precision_rounding=rounding), "The timesheet cost of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the project from SO1 should be 0.0")

        # order project should be to invoice, but nothing has been delivered yet
        project_so_2_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_2.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        self.assertTrue(float_is_zero(project_so_2_stat['amount_untaxed_invoiced'], precision_rounding=rounding), "The invoiced amount of the project from SO2 should be 0.0")
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_to_invoice'], self.so_line_order_project.price_unit * self.so_line_order_project.qty_to_invoice, precision_rounding=rounding), 0, "The amount to invoice should be the one from the SO line, as we are in ordered quantity")
        self.assertTrue(float_is_zero(project_so_2_stat['timesheet_unit_amount'], precision_rounding=rounding), "The timesheet unit amount of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['timesheet_cost'], precision_rounding=rounding), "The timesheet cost of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the project from SO2 should be 0.0")

        # fixed price project should not be impacted, as no delivered quantity are logged yet
        project_so_3_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_3.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        self.assertTrue(float_is_zero(project_so_3_stat['amount_untaxed_invoiced'], precision_rounding=rounding), "The invoiced amount of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['amount_untaxed_to_invoice'], precision_rounding=rounding), "The amount to invoice of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['timesheet_unit_amount'], precision_rounding=rounding), "The timesheet unit amount of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['timesheet_cost'], precision_rounding=rounding), "The timesheet cost of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the project from SO3 should be 0.0")

        # global project now contain 3 tasks: 'deliver' ones which have no effect (no timesheet or delivered yet), and the 'order' one which should update the 'to invoice' amount
        project_global_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', self.project_global.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        self.assertTrue(float_is_zero(project_global_stat['amount_untaxed_invoiced'], precision_rounding=rounding), "The invoiced amount of the global project should be 0.0")
        self.assertEqual(float_compare(project_global_stat['amount_untaxed_to_invoice'], self.so_line_order_task.price_unit * self.so_line_order_task.qty_to_invoice, precision_rounding=rounding), 0, "The amount to invoice of global project should take the task in 'oredered qty' into account")
        self.assertTrue(float_is_zero(project_global_stat['timesheet_unit_amount'], precision_rounding=rounding), "The timesheet unit amount of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['timesheet_cost'], precision_rounding=rounding), "The timesheet cost of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the global project should be 0.0")

        # logged some timesheets: on project only, then on tasks with different employees
        timesheet1 = self._log_timesheet_user(project_so_1, 2)
        timesheet2 = self._log_timesheet_user(project_so_2, 2)
        timesheet3 = self._log_timesheet_user(project_so_1, 3, task_so_1)
        timesheet4 = self._log_timesheet_user(project_so_2, 3, task_so_2)
        timesheet5 = self._log_timesheet_manager(project_so_1, 1, task_so_1)
        timesheet6 = self._log_timesheet_manager(project_so_2, 1, task_so_2)
        timesheet7 = self._log_timesheet_manager(self.project_global, 3, task_in_global_1)
        timesheet8 = self._log_timesheet_manager(self.project_global, 3, task_in_global_2)
        timesheet9 = self._log_timesheet_user(project_so_3, 4, task_so_3)
        self.env['project.profitability.report'].flush()

        # deliver project should now have cost and something to invoice
        project_so_1_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_1.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_so_1_timesheet_cost = timesheet1.amount + timesheet3.amount + timesheet5.amount
        project_so_1_timesheet_sold_unit = timesheet1.unit_amount + timesheet3.unit_amount + timesheet5.unit_amount
        self.assertTrue(float_is_zero(project_so_1_stat['amount_untaxed_invoiced'], precision_rounding=rounding), "The invoiced amount of the project from SO1 should be 0.0")
        self.assertEqual(float_compare(project_so_1_stat['amount_untaxed_to_invoice'], self.so_line_deliver_project.price_unit * project_so_1_timesheet_sold_unit, precision_rounding=rounding), 0, "The amount to invoice of the project from SO1 should only include timesheet linked to task")
        self.assertEqual(float_compare(project_so_1_stat['timesheet_unit_amount'], project_so_1_timesheet_sold_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the project from SO1 should include all timesheet in project")
        self.assertEqual(float_compare(project_so_1_stat['timesheet_cost'], project_so_1_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the project from SO1 should include all timesheet")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the deliver project should be 0.0")

        # order project still have something to invoice but has costs now
        project_so_2_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_2.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_so_2_timesheet_cost = timesheet2.amount + timesheet4.amount + timesheet6.amount
        project_so_2_timesheet_sold_unit = timesheet2.unit_amount + timesheet4.unit_amount + timesheet6.unit_amount
        self.assertTrue(float_is_zero(project_so_2_stat['amount_untaxed_invoiced'], precision_rounding=rounding), "The invoiced amount of the project from SO2 should be 0.0")
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_to_invoice'], self.so_line_order_project.price_unit * self.so_line_order_project.qty_to_invoice, precision_rounding=rounding), 0, "The amount to invoice should be the one from the SO line, as we are in ordered quantity")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_unit_amount'], project_so_2_timesheet_sold_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the project from SO2 should include all timesheet")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_cost'], project_so_2_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the project from SO2 should include all timesheet")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the project from SO2 should be 0.0")

        # fixed price project should ow have cost and nothing to invoice as no delivered quantity are logged yet
        project_so_3_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_3.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_so_3_timesheet_cost = timesheet9.amount
        project_so_3_timesheet_sold_unit = timesheet9.unit_amount
        self.assertTrue(float_is_zero(project_so_3_stat['amount_untaxed_invoiced'], precision_rounding=rounding), "The invoiced amount of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['amount_untaxed_to_invoice'], precision_rounding=rounding), "The amount to invoice of the project from SO3 should be 0.0")
        self.assertEqual(float_compare(project_so_3_stat['timesheet_unit_amount'], project_so_3_timesheet_sold_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the project from SO3")
        self.assertEqual(float_compare(project_so_3_stat['timesheet_cost'], project_so_3_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the project from SO3")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the project from SO3 should be 0.0")

        # global project should have more to invoice, and should now have costs
        project_global_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', self.project_global.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_global_timesheet_cost = timesheet7.amount + timesheet8.amount
        project_global_timesheet_unit = timesheet7.unit_amount + timesheet8.unit_amount
        project_global_to_invoice = (self.so_line_order_task.price_unit * self.so_line_order_task.product_uom_qty) + (self.so_line_deliver_task.price_unit * timesheet7.unit_amount)
        self.assertTrue(float_is_zero(project_global_stat['amount_untaxed_invoiced'], precision_rounding=rounding), "The invoiced amount of the global project should be 0.0")
        self.assertEqual(float_compare(project_global_stat['amount_untaxed_to_invoice'], project_global_to_invoice, precision_rounding=rounding), 0, "The amount to invoice of global project should take the task in 'oredered qty' and the delivered timesheets into account")
        self.assertEqual(float_compare(project_global_stat['timesheet_unit_amount'], project_global_timesheet_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the global project should include all timesheet")
        self.assertEqual(float_compare(project_global_stat['timesheet_cost'], project_global_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the global project should include all timesheet")
        self.assertTrue(float_is_zero(project_global_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the global project should be 0.0")

        self.so_line_deliver_manual_project.write({'qty_delivered': 7.0})
        self.env['project.profitability.report'].flush()

        # deliver project should now have cost and something to invoice
        project_so_1_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_1.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_so_1_timesheet_cost = timesheet1.amount + timesheet3.amount + timesheet5.amount
        project_so_1_timesheet_sold_unit = timesheet1.unit_amount + timesheet3.unit_amount + timesheet5.unit_amount
        self.assertTrue(float_is_zero(project_so_1_stat['amount_untaxed_invoiced'], precision_rounding=rounding), "The invoiced amount of the project from SO1 should be 0.0")
        self.assertEqual(float_compare(project_so_1_stat['amount_untaxed_to_invoice'], self.so_line_deliver_project.price_unit * project_so_1_timesheet_sold_unit, precision_rounding=rounding), 0, "The amount to invoice of the project from SO1 should only include timesheet linked to task")
        self.assertEqual(float_compare(project_so_1_stat['timesheet_unit_amount'], project_so_1_timesheet_sold_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the project from SO1 should include all timesheet in project")
        self.assertEqual(float_compare(project_so_1_stat['timesheet_cost'], project_so_1_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the project from SO1 should include all timesheet")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the deliver project should be 0.0")

        # order project still have something to invoice but has costs now
        project_so_2_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_2.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_so_2_timesheet_cost = timesheet2.amount + timesheet4.amount + timesheet6.amount
        project_so_2_timesheet_sold_unit = timesheet2.unit_amount + timesheet4.unit_amount + timesheet6.unit_amount
        self.assertTrue(float_is_zero(project_so_2_stat['amount_untaxed_invoiced'], precision_rounding=rounding), "The invoiced amount of the project from SO2 should be 0.0")
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_to_invoice'], self.so_line_order_project.price_unit * self.so_line_order_project.qty_to_invoice, precision_rounding=rounding), 0, "The amount to invoice should be the one from the SO line, as we are in ordered quantity")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_unit_amount'], project_so_2_timesheet_sold_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the project from SO2 should include all timesheet")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_cost'], project_so_2_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the project from SO2 should include all timesheet")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the project from SO2 should be 0.0")

        # fixed price project should ow have cost and something to invoice as some delivered quantity are logged in
        project_so_3_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_3.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_so_3_timesheet_cost = timesheet9.amount
        project_so_3_timesheet_sold_unit = timesheet9.unit_amount
        self.assertTrue(float_is_zero(project_so_3_stat['amount_untaxed_invoiced'], precision_rounding=rounding), "The invoiced amount of the project from SO3 should be 0.0")
        self.assertEqual(float_compare(project_so_3_stat['amount_untaxed_to_invoice'], self.so_line_deliver_manual_project.price_unit * self.so_line_deliver_manual_project.qty_to_invoice, precision_rounding=rounding), 0, "The amount to invoice of the project from SO3 should be 0.0")
        self.assertEqual(float_compare(project_so_3_stat['timesheet_unit_amount'], project_so_3_timesheet_sold_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the project from SO3")
        self.assertEqual(float_compare(project_so_3_stat['timesheet_cost'], project_so_3_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the project from SO3")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the project from SO3 should be 0.0")

        # global project should have more to invoice, and should now have costs
        project_global_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', self.project_global.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_global_timesheet_cost = timesheet7.amount + timesheet8.amount
        project_global_timesheet_unit = timesheet7.unit_amount + timesheet8.unit_amount
        project_global_to_invoice = (self.so_line_order_task.price_unit * self.so_line_order_task.product_uom_qty) + (self.so_line_deliver_task.price_unit * timesheet7.unit_amount)
        self.assertTrue(float_is_zero(project_global_stat['amount_untaxed_invoiced'], precision_rounding=rounding), "The invoiced amount of the global project should be 0.0")
        self.assertEqual(float_compare(project_global_stat['amount_untaxed_to_invoice'], project_global_to_invoice, precision_rounding=rounding), 0, "The amount to invoice of global project should take the task in 'oredered qty' and the delivered timesheets into account")
        self.assertEqual(float_compare(project_global_stat['timesheet_unit_amount'], project_global_timesheet_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the global project should include all timesheet")
        self.assertEqual(float_compare(project_global_stat['timesheet_cost'], project_global_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the global project should include all timesheet")
        self.assertTrue(float_is_zero(project_global_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the global project should be 0.0")

        InvoiceWizard = self.env['sale.advance.payment.inv'].with_context(mail_notrack=True)

        # invoice the Sales Order SO1 (based on delivered qty)
        context = {
            "active_model": 'sale.order',
            "active_ids": [self.sale_order_1.id],
            "active_id": self.sale_order_1.id,
            'open_invoices': True,
        }
        payment = InvoiceWizard.create({
            'advance_payment_method': 'delivered',
        })
        action_invoice = payment.with_context(context).create_invoices()
        invoice_id = action_invoice['res_id']
        invoice_1 = self.env['account.move'].browse(invoice_id)
        invoice_1.action_post()
        self.env['project.profitability.report'].flush()

        # deliver project should now have cost and something invoiced
        project_so_1_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_1.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_so_1_timesheet_cost = timesheet1.amount + timesheet3.amount + timesheet5.amount
        project_so_1_timesheet_sold_unit = timesheet1.unit_amount + timesheet3.unit_amount + timesheet5.unit_amount

        self.assertEqual(float_compare(project_so_1_stat['amount_untaxed_invoiced'], self.so_line_deliver_project.price_unit * project_so_1_timesheet_sold_unit, precision_rounding=rounding), 0, "The invoiced amount of the project from SO1 should only include timesheet linked to task")
        self.assertTrue(float_is_zero(project_so_1_stat['amount_untaxed_to_invoice'], precision_rounding=rounding), "The amount to invoice of the project from SO1 should be 0.0")
        self.assertEqual(float_compare(project_so_1_stat['timesheet_unit_amount'], project_so_1_timesheet_sold_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the project from SO1 should include all timesheet in project")
        self.assertEqual(float_compare(project_so_1_stat['timesheet_cost'], project_so_1_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the project from SO1 should include all timesheet")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the deliver project should be 0.0")

        # order project has still nothing invoiced
        project_so_2_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_2.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_so_2_timesheet_cost = timesheet2.amount + timesheet4.amount + timesheet6.amount
        project_so_2_timesheet_sold_unit = timesheet2.unit_amount + timesheet4.unit_amount + timesheet6.unit_amount
        self.assertTrue(float_is_zero(project_so_2_stat['amount_untaxed_invoiced'], precision_rounding=rounding), "The invoiced amount of the project from SO2 should be 0.0")
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_to_invoice'], self.so_line_order_project.price_unit * self.so_line_order_project.qty_to_invoice, precision_rounding=rounding), 0, "The amount to invoice should be the one from the SO line, as we are in ordered quantity")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_unit_amount'], project_so_2_timesheet_sold_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the project from SO2 should include all timesheet")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_cost'], project_so_2_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the project from SO2 should include all timesheet")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the project from SO2 should be 0.0")

        # fixed price project has still nothing invoice
        project_so_3_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_3.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_so_3_timesheet_cost = timesheet9.amount
        project_so_3_timesheet_sold_unit = timesheet9.unit_amount
        self.assertTrue(float_is_zero(project_so_3_stat['amount_untaxed_invoiced'], precision_rounding=rounding), "The invoiced amount of the project from SO3 should be 0.0")
        self.assertEqual(float_compare(project_so_3_stat['amount_untaxed_to_invoice'], self.so_line_deliver_manual_project.price_unit * self.so_line_deliver_manual_project.qty_to_invoice, precision_rounding=rounding), 0, "The amount to invoice of the project from SO3 should be 0.0")
        self.assertEqual(float_compare(project_so_3_stat['timesheet_unit_amount'], project_so_3_timesheet_sold_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the project from SO3")
        self.assertEqual(float_compare(project_so_3_stat['timesheet_cost'], project_so_3_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the project from SO3")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the project from SO3 should be 0.0")

        # global project should have more to invoice, and should now have costs
        project_global_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', self.project_global.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_global_timesheet_cost = timesheet7.amount + timesheet8.amount
        project_global_timesheet_unit = timesheet7.unit_amount + timesheet8.unit_amount
        project_global_to_invoice = self.so_line_order_task.price_unit * self.so_line_order_task.product_uom_qty
        project_global_invoiced = self.so_line_deliver_task.price_unit * timesheet7.unit_amount
        self.assertEqual(float_compare(project_global_stat['amount_untaxed_invoiced'], project_global_invoiced, precision_rounding=rounding), 0, "The invoiced amount of the global project should be 0.0")
        self.assertEqual(float_compare(project_global_stat['amount_untaxed_to_invoice'], project_global_to_invoice, precision_rounding=rounding), 0, "The amount to invoice of global project should take the task in 'oredered qty' and the delivered timesheets into account")
        self.assertEqual(float_compare(project_global_stat['timesheet_unit_amount'], project_global_timesheet_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the global project should include all timesheet")
        self.assertEqual(float_compare(project_global_stat['timesheet_cost'], project_global_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the global project should include all timesheet")
        self.assertTrue(float_is_zero(project_global_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the global project should be 0.0")

        # invoice the Sales Order SO2
        context = {
            "active_model": 'sale.order',
            "active_ids": [self.sale_order_2.id],
            "active_id": self.sale_order_2.id,
            'open_invoices': True,
        }
        payment = InvoiceWizard.create({
            'advance_payment_method': 'delivered',
        })
        action_invoice = payment.with_context(context).create_invoices()
        invoice_id = action_invoice['res_id']
        invoice_2 = self.env['account.move'].browse(invoice_id)
        invoice_2.action_post()
        self.env['project.profitability.report'].flush()

        # deliver project should not be impacted by the invoice of the other SO
        project_so_1_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_1.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_so_1_timesheet_cost = timesheet1.amount + timesheet3.amount + timesheet5.amount
        project_so_1_timesheet_sold_unit = timesheet1.unit_amount + timesheet3.unit_amount + timesheet5.unit_amount
        self.assertEqual(float_compare(project_so_1_stat['amount_untaxed_invoiced'], self.so_line_deliver_project.price_unit * project_so_1_timesheet_sold_unit, precision_rounding=rounding), 0, "The invoiced amount of the project from SO1 should only include timesheet linked to task")
        self.assertTrue(float_is_zero(project_so_1_stat['amount_untaxed_to_invoice'], precision_rounding=rounding), "The amount to invoice of the project from SO1 should be 0.0")
        self.assertEqual(float_compare(project_so_1_stat['timesheet_unit_amount'], project_so_1_timesheet_sold_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the project from SO1 should include all timesheet in project")
        self.assertEqual(float_compare(project_so_1_stat['timesheet_cost'], project_so_1_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the project from SO1 should include all timesheet")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the deliver project should be 0.0")

        # order project is now totally invoiced, as we are in ordered qty
        project_so_2_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_2.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_so_2_timesheet_cost = timesheet2.amount + timesheet4.amount + timesheet6.amount
        project_so_2_timesheet_sold_unit = timesheet2.unit_amount + timesheet4.unit_amount + timesheet6.unit_amount
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_invoiced'], self.so_line_order_project.price_unit * self.so_line_order_project.product_uom_qty, precision_rounding=rounding), 0, "The invoiced amount should be the one from the SO line, as we are in ordered quantity")
        self.assertTrue(float_is_zero(project_so_2_stat['amount_untaxed_to_invoice'], precision_rounding=rounding), "The amount to invoice should be the one 0.0, as all ordered quantity is invoiced")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_unit_amount'], project_so_2_timesheet_sold_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the project from SO2 should include all timesheet")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_cost'], project_so_2_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the project from SO2 should include all timesheet")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the project from SO2 should be 0.0")

        # fixed price project has still nothing invoice
        project_so_3_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_3.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_so_3_timesheet_cost = timesheet9.amount
        project_so_3_timesheet_sold_unit = timesheet9.unit_amount
        self.assertTrue(float_is_zero(project_so_3_stat['amount_untaxed_invoiced'], precision_rounding=rounding), "The invoiced amount of the project from SO3 should be 0.0")
        self.assertEqual(float_compare(project_so_3_stat['amount_untaxed_to_invoice'], self.so_line_deliver_manual_project.price_unit * self.so_line_deliver_manual_project.qty_to_invoice, precision_rounding=rounding), 0, "The amount to invoice of the project from SO3 should be 0.0")
        self.assertEqual(float_compare(project_so_3_stat['timesheet_unit_amount'], project_so_3_timesheet_sold_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the project from SO3")
        self.assertEqual(float_compare(project_so_3_stat['timesheet_cost'], project_so_3_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the project from SO3")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the project from SO3 should be 0.0")

        # global project should be totally invoiced
        project_global_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', self.project_global.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_global_timesheet_cost = timesheet7.amount + timesheet8.amount
        project_global_timesheet_unit = timesheet7.unit_amount + timesheet8.unit_amount
        project_global_invoiced = self.so_line_order_task.price_unit * self.so_line_order_task.product_uom_qty + self.so_line_deliver_task.price_unit * timesheet7.unit_amount
        self.assertEqual(float_compare(project_global_stat['amount_untaxed_invoiced'], project_global_invoiced, precision_rounding=rounding), 0, "The invoiced amount of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['amount_untaxed_to_invoice'], precision_rounding=rounding), "The amount to invoice of global project should take the task in 'oredered qty' and the delivered timesheets into account")
        self.assertEqual(float_compare(project_global_stat['timesheet_unit_amount'], project_global_timesheet_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the global project should include all timesheet")
        self.assertEqual(float_compare(project_global_stat['timesheet_cost'], project_global_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the global project should include all timesheet")
        self.assertTrue(float_is_zero(project_global_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the global project should be 0.0")

        # invoice the Sales Order SO3
        context = {
            "active_model": 'sale.order',
            "active_ids": [self.sale_order_3.id],
            "active_id": self.sale_order_3.id,
            'open_invoices': True,
        }
        payment = InvoiceWizard.create({
            'advance_payment_method': 'delivered',
        })
        action_invoice = payment.with_context(context).create_invoices()
        invoice_id = action_invoice['res_id']
        invoice_3 = self.env['account.move'].browse(invoice_id)
        invoice_3.action_post()
        self.env['project.profitability.report'].flush()

        # deliver project should not be impacted by the invoice of the other SO
        project_so_1_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_1.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_so_1_timesheet_cost = timesheet1.amount + timesheet3.amount + timesheet5.amount
        project_so_1_timesheet_sold_unit = timesheet1.unit_amount + timesheet3.unit_amount + timesheet5.unit_amount
        self.assertEqual(float_compare(project_so_1_stat['amount_untaxed_invoiced'], self.so_line_deliver_project.price_unit * project_so_1_timesheet_sold_unit, precision_rounding=rounding), 0, "The invoiced amount of the project from SO1 should only include timesheet linked to task")
        self.assertTrue(float_is_zero(project_so_1_stat['amount_untaxed_to_invoice'], precision_rounding=rounding), "The amount to invoice of the project from SO1 should be 0.0")
        self.assertEqual(float_compare(project_so_1_stat['timesheet_unit_amount'], project_so_1_timesheet_sold_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the project from SO1 should include all timesheet in project")
        self.assertEqual(float_compare(project_so_1_stat['timesheet_cost'], project_so_1_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the project from SO1 should include all timesheet")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the deliver project should be 0.0")

        # order project should not be impacted by the invoice of the other SO
        project_so_2_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_2.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_so_2_timesheet_cost = timesheet2.amount + timesheet4.amount + timesheet6.amount
        project_so_2_timesheet_sold_unit = timesheet2.unit_amount + timesheet4.unit_amount + timesheet6.unit_amount
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_invoiced'], self.so_line_order_project.price_unit * self.so_line_order_project.product_uom_qty, precision_rounding=rounding), 0, "The invoiced amount should be the one from the SO line, as we are in ordered quantity")
        self.assertTrue(float_is_zero(project_so_2_stat['amount_untaxed_to_invoice'], precision_rounding=rounding), "The amount to invoice should be the one 0.0, as all ordered quantity is invoiced")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_unit_amount'], project_so_2_timesheet_sold_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the project from SO2 should include all timesheet")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_cost'], project_so_2_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the project from SO2 should include all timesheet")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the project from SO2 should be 0.0")

        # fixed price project is now partially invoiced, as we are in delivered qty
        project_so_3_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_3.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_so_3_timesheet_cost = timesheet9.amount
        project_so_3_timesheet_sold_unit = timesheet9.unit_amount
        self.assertEqual(float_compare(project_so_3_stat['amount_untaxed_invoiced'], self.so_line_deliver_manual_project.price_unit * self.so_line_deliver_manual_project.qty_delivered, precision_rounding=rounding), 0, "The invoiced amount of the project from SO3 should be the delivered quantity * the unit price")
        self.assertTrue(float_is_zero(project_so_3_stat['amount_untaxed_to_invoice'], precision_rounding=rounding), "The amount to invoice of the project from SO3 should be 0.0")
        self.assertEqual(float_compare(project_so_3_stat['timesheet_unit_amount'], project_so_3_timesheet_sold_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the project from SO3")
        self.assertEqual(float_compare(project_so_3_stat['timesheet_cost'], project_so_3_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the project from SO3")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO3 should be 0.0")
        self.assertTrue(float_is_zero(project_so_3_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the project from SO3 should be 0.0")

        # global project should be totally invoiced
        project_global_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', self.project_global.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_global_timesheet_cost = timesheet7.amount + timesheet8.amount
        project_global_timesheet_unit = timesheet7.unit_amount + timesheet8.unit_amount
        project_global_invoiced = self.so_line_order_task.price_unit * self.so_line_order_task.product_uom_qty + self.so_line_deliver_task.price_unit * timesheet7.unit_amount
        self.assertEqual(float_compare(project_global_stat['amount_untaxed_invoiced'], project_global_invoiced, precision_rounding=rounding), 0, "The invoiced amount of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['amount_untaxed_to_invoice'], precision_rounding=rounding), "The amount to invoice of global project should take the task in 'oredered qty' and the delivered timesheets into account")
        self.assertEqual(float_compare(project_global_stat['timesheet_unit_amount'], project_global_timesheet_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the global project should include all timesheet")
        self.assertEqual(float_compare(project_global_stat['timesheet_cost'], project_global_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the global project should include all timesheet")
        self.assertTrue(float_is_zero(project_global_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the global project should be 0.0")

        # simulate the auto creation of the SO line for expense, like we confirm a vendor bill.
        so_line_expense = self.env['sale.order.line'].create({
            'name': self.product_expense.name,
            'product_id': self.product_expense.id,
            'product_uom_qty': 0.0,
            'product_uom': self.product_expense.uom_id.id,
            'price_unit': self.product_expense.list_price,  # reinvoice at sales price
            'order_id': self.sale_order_1.id,
            'is_expense': True,
        })

        # add expense AAL: 20% margin when reinvoicing
        AnalyticLine = self.env['account.analytic.line']
        expense1 = AnalyticLine.create({
            'name': 'expense on project_so_1',
            'account_id': project_so_1.analytic_account_id.id,
            'so_line': so_line_expense.id,
            'employee_id': self.employee_user.id,
            'unit_amount': 4,
            'amount': 4 * self.product_expense.list_price * -1,
            'product_id': self.product_expense.id,
            'product_uom_id': self.product_expense.uom_id.id,
        })
        expense2 = AnalyticLine.create({
            'name': 'expense on global project',
            'account_id': self.project_global.analytic_account_id.id,
            'employee_id': self.employee_user.id,
            'unit_amount': 2,
            'amount': 2 * self.product_expense.list_price * -1,
            'product_id': self.product_expense.id,
            'product_uom_id': self.product_expense.uom_id.id,
        })
        self.env['project.profitability.report'].flush()

        # deliver project should now have expense cost, and expense to reinvoice as there is a still open sales order linked to the AA1
        project_so_1_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_1.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_so_1_timesheet_cost = timesheet1.amount + timesheet3.amount + timesheet5.amount
        project_so_1_timesheet_sold_unit = timesheet1.unit_amount + timesheet3.unit_amount + timesheet5.unit_amount
        self.assertEqual(float_compare(project_so_1_stat['amount_untaxed_invoiced'], self.so_line_deliver_project.price_unit * project_so_1_timesheet_sold_unit, precision_rounding=rounding), 0, "The invoiced amount of the project from SO1 should only include timesheet linked to task")
        self.assertTrue(float_is_zero(project_so_1_stat['amount_untaxed_to_invoice'], precision_rounding=rounding), "The amount to invoice of the project from SO1 should be 0.0")
        self.assertEqual(float_compare(project_so_1_stat['timesheet_unit_amount'], project_so_1_timesheet_sold_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the project from SO1 should include all timesheet in project")
        self.assertEqual(float_compare(project_so_1_stat['timesheet_cost'], project_so_1_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the project from SO1 should include all timesheet")
        self.assertEqual(float_compare(project_so_1_stat['expense_amount_untaxed_to_invoice'], -1 * expense1.amount, precision_rounding=rounding), 0, "The expense cost to reinvoice of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertEqual(float_compare(project_so_1_stat['expense_cost'], expense1.amount, precision_rounding=rounding), 0, "The expense cost of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the deliver project should be 0.0")

        # order project is not impacted by the expenses
        project_so_2_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_2.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_so_2_timesheet_cost = timesheet2.amount + timesheet4.amount + timesheet6.amount
        project_so_2_timesheet_sold_unit = timesheet2.unit_amount + timesheet4.unit_amount + timesheet6.unit_amount
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_invoiced'], self.so_line_order_project.price_unit * self.so_line_order_project.product_uom_qty, precision_rounding=rounding), 0, "The invoiced amount should be the one from the SO line, as we are in ordered quantity")
        self.assertTrue(float_is_zero(project_so_2_stat['amount_untaxed_to_invoice'], precision_rounding=rounding), "The amount to invoice should be the one 0.0, as all ordered quantity is invoiced")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_unit_amount'], project_so_2_timesheet_sold_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the project from SO2 should include all timesheet")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_cost'], project_so_2_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the project from SO2 should include all timesheet")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the project from SO2 should be 0.0")

        # global project should have an expense, but not reinvoiceable
        project_global_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', self.project_global.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        project_global_timesheet_cost = timesheet7.amount + timesheet8.amount
        project_global_timesheet_unit = timesheet7.unit_amount + timesheet8.unit_amount
        project_global_invoiced = self.so_line_order_task.price_unit * self.so_line_order_task.product_uom_qty + self.so_line_deliver_task.price_unit * timesheet7.unit_amount
        self.assertEqual(float_compare(project_global_stat['amount_untaxed_invoiced'], project_global_invoiced, precision_rounding=rounding), 0, "The invoiced amount of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['amount_untaxed_to_invoice'], precision_rounding=rounding), "The amount to invoice of global project should take the task in 'oredered qty' and the delivered timesheets into account")
        self.assertEqual(float_compare(project_global_stat['timesheet_unit_amount'], project_global_timesheet_unit, precision_rounding=rounding), 0, "The timesheet unit amount of the global project should include all timesheet")
        self.assertEqual(float_compare(project_global_stat['timesheet_cost'], project_global_timesheet_cost, precision_rounding=rounding), 0, "The timesheet cost of the global project should include all timesheet")
        self.assertTrue(float_is_zero(project_global_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertEqual(float_compare(project_global_stat['expense_cost'], expense2.amount, precision_rounding=rounding), 0, "The expense cost of the global project should be 0.0")
        self.assertTrue(float_is_zero(project_global_stat['other_revenues'], precision_rounding=rounding), "The other revenues of the global project should be 0.0")

    def test_reversed_downpayment(self):
        # this test suppose everything is in the same currency as the current one
        currency = self.env.company.currency_id
        rounding = currency.rounding

        self.sale_order_2.action_confirm()
        context = {
            'active_model': 'sale.order',
            'active_ids': self.sale_order_2.ids,
            'active_id': self.sale_order_2.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
            'open_invoices': True,
        }
        # Let's do an invoice for a deposit of 100
        downpayment = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'percentage',
            'amount': 10,
        })
        action_invoice = downpayment.create_invoices()
        invoice_id = action_invoice['res_id']
        invoice_downpayment = self.env['account.move'].browse(invoice_id)
        invoice_downpayment.action_post()
        posted_invoice_res_ids = [invoice_id]
        downpayment2 = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'percentage',
            'amount': 25,
        })
        action_invoice = downpayment2.create_invoices()
        invoice_downpayment2 = self.env['account.move'].search(expression.AND([action_invoice['domain'], [('id', 'not in', posted_invoice_res_ids)]]))
        invoice_downpayment2.action_post()
        posted_invoice_res_ids += invoice_downpayment2.ids
        milestone_to_invoice = self.so_line_order_project.price_unit * self.so_line_order_project.qty_to_invoice
        timesheets_to_invoice = self.so_line_order_task.price_unit * self.so_line_order_task.qty_to_invoice
        total_product_price = milestone_to_invoice + timesheets_to_invoice
        credit_note_wizard = self.env['account.move.reversal'].with_context({
            'active_ids': invoice_downpayment2.ids,
            'active_id': invoice_downpayment2.id,
            'active_model': 'account.move'
        }).create({
            'refund_method': 'refund',
            'reason': 'reason test create',
            'journal_id': invoice_downpayment2.journal_id.id,
        })
        action_moves = credit_note_wizard.reverse_moves()
        credit_id = action_moves['res_id']
        invoice_credit = self.env['account.move'].browse(credit_id)
        invoice_credit.action_post()
        posted_invoice_res_ids += invoice_credit.ids
        project_so_2 = self.so_line_order_project.project_id
        task_so_2 = self.so_line_order_project.task_id
        task_in_global_2 = self.so_line_order_task.task_id

        self.env['project.profitability.report'].flush()
        project_so_2_stat = self.env['project.profitability.report'].read_group(
            [('project_id', 'in', project_so_2.ids)],
            ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'],
            ['project_id']
        )[0]
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_invoiced'], 0.1 * total_product_price, precision_rounding=rounding), 0,
                         "The invoiced amount is the amount of downpayments not reversed")
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_to_invoice'], milestone_to_invoice - 0.1 * total_product_price, precision_rounding=rounding), 0,
                         "The amount to invoice is the milestone product minus the downpayment not reversed")
        self.assertTrue(float_is_zero(project_so_2_stat['timesheet_unit_amount'], precision_rounding=rounding),
                        "The timesheet unit amount of the project from SO2 is 0")
        self.assertTrue(float_is_zero(project_so_2_stat['timesheet_cost'], precision_rounding=rounding),
                        "The timesheet cost of the project from SO2 is 0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding),
                        "The expense cost to reinvoice of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding),
                        "The expense invoiced amount of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_cost'], precision_rounding=rounding),
                        "The expense cost of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['other_revenues'], precision_rounding=rounding),
                        "The other revenues of the project from SO2 should be 0.0")

        # logged some timesheets: on project only, then on tasks with different employees
        timesheet2 = self._log_timesheet_user(project_so_2, 2)
        timesheet4 = self._log_timesheet_user(project_so_2, 3, task_so_2)
        timesheet6 = self._log_timesheet_manager(project_so_2, 2, task_so_2)
        timesheet8 = self._log_timesheet_manager(self.project_global, 3, task_in_global_2)

        # simulate the auto creation of the SO line for expense, like we confirm a vendor bill.
        so_line_expense = self.env['sale.order.line'].create({
            'name': self.product_expense.name,
            'product_id': self.product_expense.id,
            'product_uom_qty': 0.0,
            'product_uom': self.product_expense.uom_id.id,
            'price_unit': self.product_expense.list_price,  # reinvoice at sales price
            'order_id': self.sale_order_2.id,
            'is_expense': True,
        })

        expense1 = self.env['account.analytic.line'].create({
            'name': 'expense on project_so_2',
            'account_id': project_so_2.analytic_account_id.id,
            'so_line': so_line_expense.id,
            'employee_id': self.employee_user.id,
            'unit_amount': 4,
            'amount': 4 * self.product_expense.list_price * -1,
            'product_id': self.product_expense.id,
            'product_uom_id': self.product_expense.uom_id.id,
        })

        self.env['project.profitability.report'].flush()

        project_so_2_stat = self.env['project.profitability.report'].read_group(
            [('project_id', 'in', project_so_2.ids)],
            ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'],
            ['project_id']
        )[0]
        project_so_2_timesheet_cost = timesheet2.amount + timesheet4.amount + timesheet6.amount
        project_so_2_timesheet_sold_unit = timesheet2.unit_amount + timesheet4.unit_amount + timesheet6.unit_amount
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_invoiced'], 0.1 * total_product_price, precision_rounding=rounding), 0,
                         "The invoiced amount of the project from SO2 should only include downpayment not reversed")
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_to_invoice'], milestone_to_invoice - 0.1 * total_product_price, precision_rounding=rounding), 0,
                         "The amount to invoice of the project from SO2 should include the milestone to invoice minus the downpayment")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_unit_amount'], project_so_2_timesheet_sold_unit, precision_rounding=rounding), 0,
                         "The timesheet unit amount of the project from SO2 should include all timesheet in project")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_cost'], project_so_2_timesheet_cost, precision_rounding=rounding), 0,
                         "The timesheet cost of the project from SO2 should include all timesheet")
        self.assertEqual(float_compare(project_so_2_stat['expense_amount_untaxed_to_invoice'], -expense1.amount, precision_rounding=rounding), 0,
                         "The expense cost to reinvoice of the project from SO2 should be the expense amount")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding),
                        "The expense invoiced amount of the project from SO2 should be 0.0")
        self.assertEqual(float_compare(project_so_2_stat['expense_cost'], expense1.amount, precision_rounding=rounding), 0,
                         "The expense cost of the project from SO1 should be expense amount")
        self.assertTrue(float_is_zero(project_so_2_stat['other_revenues'], precision_rounding=rounding),
                        "The other revenues of the project from SO2 should be 0.0")

        # invoice the Sales Order SO2
        context = {
            "active_model": 'sale.order',
            "active_ids": self.sale_order_2.ids,
            "active_id": self.sale_order_2.id,
            'open_invoices': True,
            'mail_notrack': True,
        }
        payment = self.env['sale.advance.payment.inv'].with_context(mail_notrack=True).create({
            'advance_payment_method': 'delivered',
        })
        action_invoice = payment.with_context(context).create_invoices()
        invoice_payment = self.env['account.move'].search(expression.AND([action_invoice['domain'], [('id', 'not in', posted_invoice_res_ids)]]))
        invoice_payment.action_post()
        self.env['project.profitability.report'].flush()

        project_so_2_stat = self.env['project.profitability.report'].read_group(
            [('project_id', 'in', project_so_2.ids)],
            ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'],
            ['project_id']
        )[0]
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_invoiced'], milestone_to_invoice, precision_rounding=rounding), 0,
                         "The invoiced amount of the project from SO2 should only include timesheet linked to task")
        self.assertTrue(float_is_zero(project_so_2_stat['amount_untaxed_to_invoice'], precision_rounding=rounding),
                        "The amount to invoice of the project from SO2 should be 0.0")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_unit_amount'], project_so_2_timesheet_sold_unit, precision_rounding=rounding), 0,
                         "The timesheet unit amount of the project from SO2 should include all timesheet in project")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_cost'], project_so_2_timesheet_cost, precision_rounding=rounding), 0,
                         "The timesheet cost of the project from SO2 should include all timesheet")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding),
                        "The expense to invoice amount of the project from SO2 should be 0.0")
        self.assertEqual(float_compare(project_so_2_stat['expense_amount_untaxed_invoiced'], -1 * expense1.amount, precision_rounding=rounding), 0,
                         "The expense cost reinvoiced of the project from SO2 should be the expense amount")
        self.assertEqual(float_compare(project_so_2_stat['expense_cost'], expense1.amount, precision_rounding=rounding), 0,
                         "The expense cost of the project from SO2 should be the expense amount")
        self.assertTrue(float_is_zero(project_so_2_stat['other_revenues'], precision_rounding=rounding),
                        "The other revenues of the project from SO2 should be 0.0")

        credit_note_wizard = self.env['account.move.reversal'].with_context({
            'active_ids': invoice_payment.ids,
            'active_id': invoice_payment.id,
            'active_model': 'account.move'
        }).create({
            'refund_method': 'refund',
            'reason': 'reason test create',
            'journal_id': invoice_payment.journal_id.id,
        })
        action_moves = credit_note_wizard.reverse_moves()
        credit_id = action_moves['res_id']
        invoice_credit = self.env['account.move'].browse(credit_id)
        invoice_credit.action_post()
        self.env['project.profitability.report'].flush()

        project_so_2_stat = self.env['project.profitability.report'].read_group(
            [('project_id', 'in', project_so_2.ids)],
            ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'],
            ['project_id']
        )[0]
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_invoiced'], 0.1 * total_product_price, precision_rounding=rounding), 0,
                         "The invoiced amount of the project from SO2 should only include downpayment not reversed")
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_to_invoice'], milestone_to_invoice - 0.1 * total_product_price, precision_rounding=rounding), 0,
                         "The amount to invoice of the project from SO2 should include the milestone to invoice minus the downpayment")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_unit_amount'], project_so_2_timesheet_sold_unit, precision_rounding=rounding), 0,
                         "The timesheet unit amount of the project from SO2 should include all timesheet in project")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_cost'], project_so_2_timesheet_cost, precision_rounding=rounding), 0,
                         "The timesheet cost of the project from SO2 should include all timesheet")
        self.assertEqual(float_compare(project_so_2_stat['expense_amount_untaxed_to_invoice'], -expense1.amount, precision_rounding=rounding), 0,
                         "The expense cost to reinvoice of the project from SO2 should be the expense amount")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding),
                        "The expense invoiced amount of the project from SO2 should be 0.0")
        self.assertEqual(float_compare(project_so_2_stat['expense_cost'], expense1.amount, precision_rounding=rounding), 0,
                         "The expense cost of the project from SO1 should be expense amount")
        self.assertTrue(float_is_zero(project_so_2_stat['other_revenues'], precision_rounding=rounding),
                        "The other revenues of the project from SO2 should be 0.0")

    def test_milestone_no_tracking(self):
        # this test suppose everything is in the same currency as the current one
        currency = self.env.company.currency_id
        rounding = currency.rounding
        so_line_deliver_no_task = self.env['sale.order.line'].create({
            'name': self.product_delivery_manual1.name,
            'product_id': self.product_delivery_manual1.id,
            'product_uom_qty': 50,
            'product_uom': self.product_delivery_manual1.uom_id.id,
            'price_unit': self.product_delivery_manual1.list_price,
            'order_id': self.sale_order_2.id,
        })
        so_line_deliver_no_task.write({'qty_delivered': 1.0})
        self.sale_order_2.action_confirm()
        milestone_to_invoice = self.so_line_order_project.price_unit * self.so_line_order_project.qty_to_invoice
        milestone_no_task = so_line_deliver_no_task.price_unit * so_line_deliver_no_task.qty_to_invoice
        self.env['project.profitability.report'].flush()

        project_so_2 = self.so_line_order_project.project_id
        project_so_2_stat = self.env['project.profitability.report'].read_group(
            [('project_id', 'in', project_so_2.ids)],
            ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'],
            ['project_id']
        )[0]
        self.assertTrue(float_is_zero(project_so_2_stat['amount_untaxed_invoiced'], precision_rounding=rounding),
                         "The invoiced amount of the project from SO2 should be 0.0")
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_to_invoice'], milestone_to_invoice + milestone_no_task, precision_rounding=rounding), 0,
                         "The amount to invoice of the project from SO2 should include the milestone to invoice")
        self.assertTrue(float_is_zero(project_so_2_stat['timesheet_unit_amount'], precision_rounding=rounding),
                        "The timesheet unit amount of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['timesheet_cost'], precision_rounding=rounding),
                        "The timesheet cost of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding),
                        "The expense cost to reinvoice of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding),
                        "The expense invoiced amount of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_cost'], precision_rounding=rounding),
                        "The expense cost of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['other_revenues'], precision_rounding=rounding),
                        "The other revenues of the project from SO2 should be 0.0")

        task_using_milestone_not_tracked = self.env['project.task'].create({
            'name': 'Task with milestone not tracked',
            'project_id': project_so_2.id,
            'partner_id': project_so_2.partner_id.id,
            'sale_line_id': so_line_deliver_no_task.id,
        })
        self.env['project.profitability.report'].flush()
        project_so_2_stat = self.env['project.profitability.report'].read_group(
            [('project_id', 'in', project_so_2.ids)],
            ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'],
            ['project_id']
        )[0]
        self.assertTrue(float_is_zero(project_so_2_stat['amount_untaxed_invoiced'], precision_rounding=rounding),
                        "The invoiced amount of the project from SO2 should be 0.0")
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_to_invoice'], milestone_to_invoice + milestone_no_task, precision_rounding=rounding), 0,
                         "The amount to invoice of the project from SO2 should include the milestone to invoice linked to the project or project's task")
        self.assertTrue(float_is_zero(project_so_2_stat['timesheet_unit_amount'], precision_rounding=rounding),
                        "The timesheet unit amount of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['timesheet_cost'], precision_rounding=rounding),
                        "The timesheet cost of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding),
                        "The expense cost to reinvoice of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding),
                        "The expense invoiced amount of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_cost'], precision_rounding=rounding),
                        "The expense cost of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['other_revenues'], precision_rounding=rounding),
                        "The other revenues of the project from SO2 should be 0.0")

        timesheet = self._log_timesheet_user(project_so_2, 3, task_using_milestone_not_tracked)
        self.env['project.profitability.report'].flush()
        project_so_2_stat = self.env['project.profitability.report'].read_group(
            [('project_id', 'in', project_so_2.ids)],
            ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'],
            ['project_id']
        )[0]
        project_so_2_timesheet_cost = timesheet.amount
        project_so_2_timesheet_sold_unit = timesheet.unit_amount
        self.assertTrue(float_is_zero(project_so_2_stat['amount_untaxed_invoiced'], precision_rounding=rounding),
                        "The invoiced amount of the project from SO2 should only include downpayment not reversed")
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_to_invoice'], milestone_to_invoice + milestone_no_task, precision_rounding=rounding), 0,
                         "The amount to invoice of the project from SO2 should include the milestone to invoice minus the downpayment")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_unit_amount'], project_so_2_timesheet_sold_unit, precision_rounding=rounding), 0,
                         "The timesheet unit amount of the project from SO2 should include all timesheet in project")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_cost'], project_so_2_timesheet_cost, precision_rounding=rounding), 0,
                         "The timesheet cost of the project from SO2 should include all timesheet")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding),
                        "The expense cost to reinvoice of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding),
                        "The expense invoiced amount of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_cost'], precision_rounding=rounding),
                        "The expense cost of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['other_revenues'], precision_rounding=rounding),
                        "The other revenues of the project from SO2 should be 0.0")
        # invoice the Sales Order SO2
        context = {
            "active_model": 'sale.order',
            "active_ids": self.sale_order_2.ids,
            "active_id": self.sale_order_2.id,
            'open_invoices': True,
            'mail_notrack': True,
        }
        payment = self.env['sale.advance.payment.inv'].with_context(mail_notrack=True).create({
            'advance_payment_method': 'delivered',
        })
        action_invoice = payment.with_context(context).create_invoices()
        invoice_payment = self.env['account.move'].browse(action_invoice['res_id'])
        invoice_payment.action_post()
        self.env['project.profitability.report'].flush()
        project_so_2_stat = self.env['project.profitability.report'].read_group(
            [('project_id', 'in', project_so_2.ids)],
            ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'],
            ['project_id']
        )[0]
        self.assertEqual(float_compare(project_so_2_stat['amount_untaxed_invoiced'], milestone_to_invoice + milestone_no_task, precision_rounding=rounding), 0,
                         "The invoiced amount of the project from SO2 should include the milestone invoiced")
        self.assertTrue(float_is_zero(project_so_2_stat['amount_untaxed_to_invoice'], precision_rounding=rounding),
                        "The amount to invoice of the project from SO2 should include the milestone to invoice")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_unit_amount'], project_so_2_timesheet_sold_unit, precision_rounding=rounding), 0,
                         "The timesheet unit amount of the project from SO2 should include all timesheet in project")
        self.assertEqual(float_compare(project_so_2_stat['timesheet_cost'], project_so_2_timesheet_cost, precision_rounding=rounding), 0,
                         "The timesheet cost of the project from SO2 should include all timesheet")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding),
                        "The expense cost to reinvoice of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding),
                        "The expense invoiced amount of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['expense_cost'], precision_rounding=rounding),
                        "The expense cost of the project from SO2 should be 0.0")
        self.assertTrue(float_is_zero(project_so_2_stat['other_revenues'], precision_rounding=rounding),
                        "The other revenues of the project from SO2 should be 0.0")

    def test_profitability_credit_note_bill(self):
        """Test whether the profitability is zeroed by credit note on a vendor bill."""
        ProjectProfitabilityReport = self.env['project.profitability.report']
        analytic_account = self.project_global.analytic_account_id
        product = self.env['product.product'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'name': "Product",
            'standard_price': 100.0,
            'list_price': 100.0,
            'taxes_id': False,
        })
        test_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'currency_id': self.env.user.company_id.currency_id,
            'partner_id': self.partner_a,
            'invoice_date': '2021-01-01',
            'invoice_line_ids': [(0, 0, {
                'quantity': 1,
                'product_id': product.id,
                'price_unit': 100.0,
                'analytic_account_id': analytic_account.id,
            })]
        })
        test_bill.action_post()
        ProjectProfitabilityReport.flush()

        project_stat= ProjectProfitabilityReport.read_group([('project_id', 'in', self.project_global.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        self.assertAlmostEqual(project_stat['amount_untaxed_invoiced'], 0, msg="The invoiced amount of the project should be zero, before credit note.")
        self.assertAlmostEqual(project_stat['amount_untaxed_to_invoice'], 0, msg="The amount to invoice of the project should be zero, before credit note.")
        self.assertAlmostEqual(project_stat['timesheet_unit_amount'], 0, msg="The timesheet unit amount of the project should be zero, before credit note.")
        self.assertAlmostEqual(project_stat['timesheet_cost'], 0, msg="The timesheet cost of the project should be zero, before credit note.")
        self.assertAlmostEqual(project_stat['expense_amount_untaxed_to_invoice'], 0, msg="The expense cost to reinvoice of the project should be zero, before credit note.")
        self.assertAlmostEqual(project_stat['expense_amount_untaxed_invoiced'], 0, msg="The expense invoiced amount of the project should be zero, before credit note.")
        self.assertAlmostEqual(project_stat['expense_cost'], test_bill.amount_total_signed, msg="The expense cost of the project should be equal to the the invoice line price, before credit note.")
        self.assertAlmostEqual(project_stat['other_revenues'], 0, msg="The other revenues of the project should be zero, before credit note")

        credit_note_wizard = self.env['account.move.reversal'].with_context({
            'active_model': 'account.move',
            'active_ids': test_bill.ids,
            'active_id': test_bill.id,
        }).create({
            'refund_method': 'cancel',
            'reason': 'no reason',
            'journal_id': self.company_data['default_journal_purchase'].id
        })
        credit_note_wizard.reverse_moves()
        ProjectProfitabilityReport.flush()

        project_stat= ProjectProfitabilityReport.read_group([('project_id', 'in', self.project_global.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        self.assertAlmostEqual(project_stat['amount_untaxed_invoiced'], 0, msg="The invoiced amount of the project should be zero, after credit note.")
        self.assertAlmostEqual(project_stat['amount_untaxed_to_invoice'], 0, msg="The amount to invoice of the project should be zero, after credit note.")
        self.assertAlmostEqual(project_stat['timesheet_unit_amount'], 0, msg="The timesheet unit amount of the project should be zero, after credit note.")
        self.assertAlmostEqual(project_stat['timesheet_cost'], 0, msg="The timesheet cost of the project should be zero, after credit note.")
        self.assertAlmostEqual(project_stat['expense_amount_untaxed_to_invoice'], 0, msg="The expense cost to reinvoice of the project should be zero, after credit note.")
        self.assertAlmostEqual(project_stat['expense_amount_untaxed_invoiced'], 0, msg="The expense invoiced amount of the project should be zero, after credit note.")
        self.assertAlmostEqual(project_stat['expense_cost'], 0, msg="The expense cost of the project should be zero, as it is balanced by credit note.")
        self.assertAlmostEqual(project_stat['other_revenues'], 0, msg="The other revenues (credit note) of the project should be zero (not taken into account), after credit note.")

    def test_profitability_credit_note_invoice(self):
        """Test whether the profitability doesn't change with customer invoice or its credit note."""
        ProjectProfitabilityReport = self.env['project.profitability.report']
        analytic_account = self.project_global.analytic_account_id
        product = self.env['product.product'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'name': "Product",
            'standard_price': 100.0,
            'list_price': 100.0,
            'taxes_id': False,
        })
        test_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'currency_id': self.env.user.company_id.currency_id,
            'partner_id': self.partner_a,
            'invoice_date': '2021-01-01',
            'invoice_line_ids': [(0, 0, {
                'quantity': 1,
                'product_id': product.id,
                'price_unit': 100.0,
                'analytic_account_id': analytic_account.id,
            })]
        })
        test_invoice.action_post()
        ProjectProfitabilityReport.flush()

        project_stat= ProjectProfitabilityReport.read_group([('project_id', 'in', self.project_global.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        self.assertAlmostEqual(project_stat['amount_untaxed_invoiced'], 0, msg="The invoiced amount of the project should be zero, before credit note.")
        self.assertAlmostEqual(project_stat['amount_untaxed_to_invoice'], 0, msg="The amount to invoice of the project should be zero, before credit note.")
        self.assertAlmostEqual(project_stat['timesheet_unit_amount'], 0, msg="The timesheet unit amount of the project should be zero, before credit note.")
        self.assertAlmostEqual(project_stat['timesheet_cost'], 0, msg="The timesheet cost of the project should be zero, before credit note.")
        self.assertAlmostEqual(project_stat['expense_amount_untaxed_to_invoice'], 0, msg="The expense cost to reinvoice of the project should be zero, before credit note.")
        self.assertAlmostEqual(project_stat['expense_amount_untaxed_invoiced'], 0, msg="The expense invoiced amount of the project should be zero, before credit note.")
        self.assertAlmostEqual(project_stat['expense_cost'], 0, msg="The expense cost of the project should be zero, before credit note.")
        self.assertAlmostEqual(project_stat['other_revenues'], test_invoice.amount_total_signed, msg="The other revenues of the project should be equal to the the invoice line price, after credit note.")

        credit_note_wizard = self.env['account.move.reversal'].with_context({
            'active_model': 'account.move',
            'active_ids': test_invoice.ids,
            'active_id': test_invoice.id,
        }).create({
            'refund_method': 'cancel',
            'reason': 'no reason',
            'journal_id': self.company_data['default_journal_sale'].id
        })
        credit_note_wizard.reverse_moves()
        ProjectProfitabilityReport.flush()

        project_stat= ProjectProfitabilityReport.read_group([('project_id', 'in', self.project_global.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        self.assertAlmostEqual(project_stat['amount_untaxed_invoiced'], 0, msg="The invoiced amount of the project should be zero, after credit note.")
        self.assertAlmostEqual(project_stat['amount_untaxed_to_invoice'], 0, msg="The amount to invoice of the project should be zero, after credit note.")
        self.assertAlmostEqual(project_stat['timesheet_unit_amount'], 0, msg="The timesheet unit amount of the project should be zero, after credit note.")
        self.assertAlmostEqual(project_stat['timesheet_cost'], 0, msg="The timesheet cost of the project should be zero, after credit note.")
        self.assertAlmostEqual(project_stat['expense_amount_untaxed_to_invoice'], 0, msg="The expense cost to reinvoice of the project should be zero, after credit note.")
        self.assertAlmostEqual(project_stat['expense_amount_untaxed_invoiced'], 0, msg="The expense invoiced amount of the project should be zero, after credit note.")
        self.assertAlmostEqual(project_stat['expense_cost'], 0, msg="The expense costs (credit note) of the project should be zero (not taken into account), after credit note.")
        self.assertAlmostEqual(project_stat['other_revenues'], 0, msg="The other revenues of the project should be zero, as it is balanced by credit note.")

    def test_project_profitability_report(self):
        """ Test profitability report for a project with a task and a SO with a service and a product
            added linked to the task."""

        # create Analytic Accounts
        self.analytic_account_1 = self.env['account.analytic.account'].create({
            'name': 'Test AA 1',
            'code': 'AA1',
            'company_id': self.company_data['company'].id,
            'partner_id': self.partner_a.id
        })

        self.sale_order_1 = self.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'analytic_account_id': self.analytic_account_1.id,
        })
        self.so_line_deliver_project = self.env['sale.order.line'].create({
            'name': self.product_delivery_timesheet3.name,
            'product_id': self.product_delivery_timesheet3.id,
            'product_uom': self.product_delivery_timesheet3.uom_id.id,
            'price_unit': self.product_delivery_timesheet3.list_price,
            'order_id': self.sale_order_1.id,
        })
        self.so_line_deliver_task = self.env['sale.order.line'].create({
            'name': self.product_delivery_timesheet2.name,
            'product_id': self.product_delivery_timesheet2.id,
            'product_uom': self.product_delivery_timesheet2.uom_id.id,
            'price_unit': self.product_delivery_timesheet2.list_price,
            'order_id': self.sale_order_1.id,
        })

        # this test suppose everything is in the same currency as the current one
        currency = self.env.company.currency_id
        rounding = currency.rounding
        # confirm sales orders
        self.sale_order_1.action_confirm()
        self.env['project.profitability.report'].flush()

        project_so_1 = self.so_line_deliver_project.project_id

        task_so_1 = self.so_line_deliver_project.task_id

        self.product_material = self.env['product.product'].create({
            'name': 'My Material Product',
            'sale_ok': True,
            'invoice_policy': 'order',
            'lst_price': 5,
        })

        self.env['sale.order.line'].create({
            'order_id': self.sale_order_1.id,
            'name': self.product_material.name,
            'product_id': self.product_material.id,
            'product_uom_qty': 5,
            'product_uom': self.product_material.uom_id.id,
            'price_unit': self.product_material.list_price,
            'task_id': task_so_1.id,
        })

        InvoiceWizard = self.env['sale.advance.payment.inv'].with_context(mail_notrack=True)

        # invoice the Sales Order SO1 (based on delivered qty)
        context = {
            "active_model": 'sale.order',
            "active_ids": [self.sale_order_1.id],
            "active_id": self.sale_order_1.id,
            'open_invoices': True,
        }
        payment = InvoiceWizard.create({
            'advance_payment_method': 'delivered',
        })
        action_invoice = payment.with_context(context).create_invoices()
        invoice_id = action_invoice['res_id']
        invoice_1 = self.env['account.move'].browse(invoice_id)
        invoice_1.action_post()

        project_so_1_stat = self.env['project.profitability.report'].read_group([('project_id', 'in', project_so_1.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_unit_amount', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_to_invoice', 'expense_amount_untaxed_invoiced', 'other_revenues'], ['project_id'])[0]
        self.assertTrue(float_is_zero(project_so_1_stat['amount_untaxed_invoiced'], precision_rounding=rounding), "The invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['amount_untaxed_to_invoice'], precision_rounding=rounding), "The amount to invoice of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['timesheet_unit_amount'], precision_rounding=rounding), "The timesheet unit amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['timesheet_cost'], precision_rounding=rounding), "The timesheet cost of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_amount_untaxed_to_invoice'], precision_rounding=rounding), "The expense cost to reinvoice of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_amount_untaxed_invoiced'], precision_rounding=rounding), "The expense invoiced amount of the project from SO1 should be 0.0")
        self.assertTrue(float_is_zero(project_so_1_stat['expense_cost'], precision_rounding=rounding), "The expense cost of the project from SO1 should be 0.0")
        self.assertEqual(float_compare(project_so_1_stat['other_revenues'], invoice_1.amount_untaxed, precision_rounding=rounding), 0, "The other revenues of the project from SO1 should be the same as the untaxed amount in invoice")
