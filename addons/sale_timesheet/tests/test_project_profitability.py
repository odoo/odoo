# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from .common import TestCommonSaleTimesheet


@tagged('-at_install', 'post_install')
class TestSaleTimesheetProjectProfitability(TestCommonSaleTimesheet):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.task = cls.env['project.task'].create({
            'name': 'Test',
            'project_id': cls.project_task_rate.id,
        })
        cls.project_profitability_items_empty = {
            'revenues': {'data': [], 'total': {'to_invoice': 0.0, 'invoiced': 0.0}},
            'costs': {'data': [], 'total': {'to_bill': 0.0, 'billed': 0.0}},
        }

    def test_profitability_of_non_billable_project(self):
        """ Test no data is found for the project profitability since the project is not billable
            even if it is linked to a sale order items.
        """
        self.assertFalse(self.project_non_billable.allow_billable)
        self.assertDictEqual(
            self.project_non_billable._get_profitability_items(False),
            self.project_profitability_items_empty,
        )
        self.project_non_billable.write({'sale_line_id': self.so.order_line[0].id})
        self.assertDictEqual(
            self.project_non_billable._get_profitability_items(False),
            self.project_profitability_items_empty,
            "Even if the project has a sale order item linked the project profitability should not be computed since it is not billable."
        )

    def test_get_project_profitability_items(self):
        """ Test _get_project_profitability_items method to ensure the project profitability
            is correctly computed as expected.
        """
        sale_order = self.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': self.partner_b.id,
            'partner_invoice_id': self.partner_b.id,
            'partner_shipping_id': self.partner_b.id,
        })
        SaleOrderLine = self.env['sale.order.line'].with_context(tracking_disable=True, default_order_id=sale_order.id)
        delivery_service_order_line = SaleOrderLine.create({
            'product_id': self.product_delivery_manual1.id,
            'product_uom_qty': 5,
        })
        sale_order.action_confirm()
        self.task.write({'sale_line_id': delivery_service_order_line.id})
        self.assertDictEqual(
            self.project_task_rate._get_profitability_items(False),
            self.project_profitability_items_empty,
            'No timesheets has been recorded in the task and no product has been deelivered in the SO linked so the project profitability has no data found.'
        )

        Timesheet = self.env['account.analytic.line'].with_context(
            default_task_id=self.task.id,
        )
        timesheet1 = Timesheet.create({
            'name': 'Timesheet 1',
            'employee_id': self.employee_user.id,
            'project_id': self.project_task_rate.id,
            'unit_amount': 3.0,
        })
        timesheet2 = Timesheet.create({
            'name': 'Timesheet 2',
            'employee_id': self.employee_user.id,
            'project_id': self.project_task_rate.id,
            'unit_amount': 2.0,
        })

        sequence_per_invoice_type = self.project_task_rate._get_profitability_sequence_per_invoice_type()
        self.assertIn('billable_time', sequence_per_invoice_type)
        self.assertIn('billable_fixed', sequence_per_invoice_type)
        self.assertIn('billable_milestones', sequence_per_invoice_type)
        self.assertIn('billable_manual', sequence_per_invoice_type)

        self.assertEqual(self.task.sale_line_id, delivery_service_order_line)
        self.assertEqual((timesheet1 + timesheet2).so_line, delivery_service_order_line)
        self.assertEqual(delivery_service_order_line.qty_delivered, 0.0, 'The service type is not timesheet but manual so the quantity delivered is not increased by the timesheets linked.')
        self.assertDictEqual(
            self.project_task_rate._get_profitability_items(False),
            {
                'revenues': {
                    'data': [],
                    'total': {'to_invoice': 0.0, 'invoiced': 0.0},
                },
                'costs': {
                    'data': [
                        {
                            'id': 'billable_manual',
                            'sequence': sequence_per_invoice_type['billable_manual'],
                            'billed': (timesheet1.unit_amount + timesheet2.unit_amount) * -self.employee_user.hourly_cost,
                            'to_bill': 0.0,
                        },
                    ],
                    'total': {
                        'to_bill': 0.0,
                        'billed': (timesheet1.unit_amount + timesheet2.unit_amount) * -self.employee_user.hourly_cost
                    },
                },
            }
        )

        timesheet3 = Timesheet.create({
            'name': 'Timesheet 3',
            'employee_id': self.employee_manager.id,
            'project_id': self.project_task_rate.id,
            'unit_amount': 1.0,
            'so_line': False,
            'is_so_line_edited': True,
        })
        self.assertFalse(timesheet3.so_line, 'This timesheet should be non billable since the user manually empty the SOL.')

        self.assertDictEqual(
            self.project_task_rate._get_profitability_items(False),
            {
                'revenues': {
                    'data': [],
                    'total': {'to_invoice': 0.0, 'invoiced': 0.0},
                },
                'costs': {
                    'data': [
                        {
                            'id': 'billable_manual',
                            'sequence': sequence_per_invoice_type['billable_manual'],
                            'billed': (timesheet1.unit_amount + timesheet2.unit_amount) * -self.employee_user.hourly_cost,
                            'to_bill': 0.0,
                        },
                        {
                            'id': 'non_billable',
                            'sequence': sequence_per_invoice_type['non_billable'],
                            'billed': timesheet3.unit_amount * -self.employee_manager.hourly_cost,
                            'to_bill': 0.0,
                        },
                    ],
                    'total': {
                        'to_bill': 0.0,
                        'billed':
                            (timesheet1.unit_amount + timesheet2.unit_amount) * -self.employee_user.hourly_cost
                            + timesheet3.unit_amount * -self.employee_manager.hourly_cost,
                    },
                },
            },
            'The previous costs should remains and the cost of the third timesheet should be added.'
        )

        delivery_timesheet_order_line = SaleOrderLine.create({
            'product_id': self.product_delivery_timesheet1.id,
            'product_uom_qty': 5,
        })
        self.task.write({'sale_line_id': delivery_timesheet_order_line.id})
        billable_timesheets = timesheet1 + timesheet2
        self.assertEqual(billable_timesheets.so_line, delivery_timesheet_order_line, 'The SOL of the timesheets should be the one of the task.')
        self.assertEqual(delivery_timesheet_order_line.qty_delivered, timesheet1.unit_amount + timesheet2.unit_amount)
        self.assertEqual(
            self.project_task_rate._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
                        {'id': 'billable_time', 'sequence': sequence_per_invoice_type['billable_time'], 'to_invoice': delivery_timesheet_order_line.untaxed_amount_to_invoice, 'invoiced': 0.0},
                    ],
                    'total': {'to_invoice': delivery_timesheet_order_line.untaxed_amount_to_invoice, 'invoiced': 0.0},
                },
                'costs': {
                    'data': [
                        {
                            'id': 'billable_time',
                            'sequence': sequence_per_invoice_type['billable_time'],
                            'billed': (timesheet1.unit_amount + timesheet2.unit_amount) * -self.employee_user.hourly_cost,
                            'to_bill': 0.0,
                        },
                        {
                            'id': 'non_billable',
                            'sequence': sequence_per_invoice_type['non_billable'],
                            'billed': timesheet3.unit_amount * -self.employee_manager.hourly_cost,
                            'to_bill': 0.0,
                        },
                    ],
                    'total': {
                        'to_bill': 0.0,
                        'billed':
                            (timesheet1.unit_amount + timesheet2.unit_amount) * -self.employee_user.hourly_cost
                            + timesheet3.unit_amount * -self.employee_manager.hourly_cost,
                    },
                },
            },
        )
        milestone_order_line = SaleOrderLine.create({
            'product_id': self.product_milestone.id,
            'product_uom_qty': 1,
        })
        task2 = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test',
            'project_id': self.project_task_rate.id,
            'sale_line_id': milestone_order_line.id,
        })
        task2_timesheet = Timesheet.with_context(default_task_id=task2.id).create({
            'name': '/',
            'project_id': self.project_task_rate.id,
            'employee_id': self.employee_user.id,
            'unit_amount': 1,
        })
        self.assertEqual(task2_timesheet.so_line, milestone_order_line)
        profitability_items = self.project_task_rate._get_profitability_items(False)
        self.assertFalse([data for data in profitability_items['revenues']['data'] if data['id'] == 'billable_milestones'])
        self.assertDictEqual(
            [data for data in profitability_items['costs']['data'] if data['id'] == 'billable_milestones'][0],
            {'id': 'billable_milestones', 'sequence': sequence_per_invoice_type['billable_milestones'], 'to_bill': 0.0, 'billed': task2_timesheet.amount},
        )

        milestone_order_line.qty_delivered = 1
        profitability_items = self.project_task_rate._get_profitability_items(False)
        self.assertDictEqual(
            [data for data in profitability_items['revenues']['data'] if data['id'] == 'billable_milestones'][0],
            {'id': 'billable_milestones', 'sequence': sequence_per_invoice_type['billable_milestones'], 'to_invoice': milestone_order_line.untaxed_amount_to_invoice, 'invoiced': 0.0},
        )
        task2_timesheet.unlink()
        profitability_items = self.project_task_rate._get_profitability_items(False)
        self.assertFalse([data for data in profitability_items['revenues']['data'] if data['id'] == 'billable_milestones'])
        self.assertFalse([data for data in profitability_items['costs']['data'] if data['id'] == 'billable_milestones'])
