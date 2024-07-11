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
        cls.foreign_currency = cls.env['res.currency'].create({
            'name': 'Chaos orb',
            'symbol': '☺',
            'rounding': 0.001,
            'position': 'after',
            'currency_unit_label': 'Chaos',
            'currency_subunit_label': 'orb',
        })
        cls.env['res.currency.rate'].create({
            'name': '2016-01-01',
            'rate': '5.0',
            'currency_id': cls.foreign_currency.id,
            'company_id': cls.env.company.id,
        })

    def test_get_project_profitability_items(self):
        """ Test _get_project_profitability_items method to ensure the project profitability
            is computed as expected.
        """
        foreign_company = self.company_data_2['company']
        foreign_company.currency_id = self.foreign_currency
        self.project_task_rate.analytic_account_id.company_id = False
        self.project_task_rate.company_id = False

        # Create and confirm a SO with the main company
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

        # Create and confirm a SO with the foreign company
        sale_order_foreign = self.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': self.partner_b.id,
            'partner_invoice_id': self.partner_b.id,
            'partner_shipping_id': self.partner_b.id,
            'company_id': foreign_company.id,
        })
        sale_order_foreign.currency_id = foreign_company.currency_id
        SaleOrderLineForeign = self.env['sale.order.line'].with_context(tracking_disable=True, default_order_id=sale_order_foreign.id)
        SaleOrderLineForeign.create({
            'product_id': self.product_delivery_manual1.id,
            'product_uom_qty': 5,
        })
        sale_order_foreign.action_confirm()
        self.task.write({'sale_line_id': delivery_service_order_line.id})
        # Create the foreign users needed for the foreign timesheets
        foreign_partner = self.env['res.partner'].create({
            'name': 'Foreign Employee address',
            'company_id': foreign_company.id,
        })
        foreign_employee = self.env['hr.employee'].create({
            'name': 'test',
            'company_id': foreign_company.id,
            'work_contact_id': foreign_partner.id,
            'hourly_cost': 200,
        })
        foreign_employee_2 = self.env['hr.employee'].create({
            'name': 'test',
            'company_id': foreign_company.id,
            'work_contact_id': foreign_partner.id,
            'hourly_cost': 500,
        })
        # Create 2 new timesheets linked to the task of the project
        Timesheet = self.env['account.analytic.line'].with_context(
            default_task_id=self.task.id,
        )
        foreign_timesheet1 = Timesheet.create({
            'name': 'Foreign Timesheet 1',
            'employee_id': foreign_employee.id,
            'project_id': self.project_task_rate.id,
            'unit_amount': 3.0,
            'company_id': foreign_company.id,
        })
        foreign_timesheet2 = Timesheet.create({
            'name': 'Foreign Timesheet 2',
            'employee_id': foreign_employee.id,
            'project_id': self.project_task_rate.id,
            'unit_amount': 2.0,
            'company_id': foreign_company.id,
        })

        sequence_per_invoice_type = self.project_task_rate._get_profitability_sequence_per_invoice_type()
        self.assertIn('billable_time', sequence_per_invoice_type)
        self.assertIn('billable_fixed', sequence_per_invoice_type)
        self.assertIn('billable_milestones', sequence_per_invoice_type)
        self.assertIn('billable_manual', sequence_per_invoice_type)
        self.assertEqual(self.task.sale_line_id, delivery_service_order_line)
        self.assertEqual((foreign_timesheet1 + foreign_timesheet2).so_line, delivery_service_order_line)
        self.assertEqual(delivery_service_order_line.qty_delivered, 0.0, 'The service type is not timesheet but manual so the quantity delivered is not increased by the timesheets linked.')

        # Adding an extra cost/revenue to ensure those are computed correctly.
        self.env['account.analytic.line'].create([{
            'name': 'other revenues line',
            'account_id': self.project_task_rate.analytic_account_id.id,
            'amount': 100,
        }, {
            'name': 'other costs line',
            'account_id': self.project_task_rate.analytic_account_id.id,
            'amount': -100,
        }])
        self.assertDictEqual(
            self.project_task_rate._get_profitability_items(False),
            {
                'revenues': {
                    'data': [{'id': 'other_revenues', 'sequence': sequence_per_invoice_type['other_revenues'], 'invoiced': 100.0, 'to_invoice': 0.0}],
                    'total': {'invoiced': 100.0, 'to_invoice': 0.0},
                },
                'costs': {
                    'data': [
                        {'id': 'other_costs', 'sequence': sequence_per_invoice_type['other_costs'], 'billed': -100.0, 'to_bill': 0.0},
                        {
                            'id': 'billable_manual',
                            'sequence': sequence_per_invoice_type['billable_manual'],
                            'billed': (foreign_timesheet1.unit_amount + foreign_timesheet2.unit_amount) * -foreign_employee.hourly_cost * 0.2,
                            'to_bill': 0.0,
                        },
                    ],
                    'total': {
                        'to_bill': 0.0,
                        'billed': -100 + (foreign_timesheet1.unit_amount + foreign_timesheet2.unit_amount) * -foreign_employee.hourly_cost * 0.2
                    },
                },
            }
        )

        # Create 2 new timesheets linked to the task of the project
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
        self.assertEqual((timesheet1 + timesheet2).so_line, delivery_service_order_line)
        self.assertEqual(delivery_service_order_line.qty_delivered, 0.0, 'The service type is not timesheet but manual so the quantity delivered is not increased by the timesheets linked.')

        self.assertDictEqual(
            self.project_task_rate._get_profitability_items(False),
            {
                'revenues': {
                    'data': [{'id': 'other_revenues', 'sequence': sequence_per_invoice_type['other_revenues'], 'invoiced': 100.0, 'to_invoice': 0.0}],
                    'total': {'invoiced': 100.0, 'to_invoice': 0.0},
                },
                'costs': {
                    'data': [
                        {'id': 'other_costs', 'sequence': sequence_per_invoice_type['other_costs'], 'billed': -100.0, 'to_bill': 0.0},
                        {
                            'id': 'billable_manual',
                            'sequence': sequence_per_invoice_type['billable_manual'],
                            'billed': (timesheet1.unit_amount + timesheet2.unit_amount) * -self.employee_user.hourly_cost +
                                      (foreign_timesheet1.unit_amount + foreign_timesheet2.unit_amount) * -foreign_employee.hourly_cost * 0.2,
                            'to_bill': 0.0,
                        },
                    ],
                    'total': {
                        'to_bill': 0.0,
                        'billed': -100 + (timesheet1.unit_amount + timesheet2.unit_amount) * -self.employee_user.hourly_cost +
                                  (foreign_timesheet1.unit_amount + foreign_timesheet2.unit_amount) * -foreign_employee.hourly_cost * 0.2
                    },
                },
            }
        )

        # Create a 3rd foreign timesheet and manually update it.
        foreign_timesheet3 = Timesheet.create({
            'name': 'Foreign_Timesheet 3',
            'employee_id': foreign_employee_2.id,
            'project_id': self.project_task_rate.id,
            'unit_amount': 1.0,
            'so_line': False,
            'is_so_line_edited': True,
            'company_id': foreign_company.id,
        })
        self.assertFalse(foreign_timesheet3.so_line, 'This timesheet should be non billable since the user manually empty the SOL.')
        self.assertDictEqual(
            self.project_task_rate._get_profitability_items(False),
            {
                'revenues': {
                    'data': [{'id': 'other_revenues', 'sequence': sequence_per_invoice_type['other_revenues'], 'invoiced': 100.0, 'to_invoice': 0.0}],
                    'total': {'invoiced': 100.0, 'to_invoice': 0.0},
                },
                'costs': {
                    'data': [
                        {'id': 'other_costs', 'sequence': sequence_per_invoice_type['other_costs'], 'billed': -100.0, 'to_bill': 0.0},
                        {
                            'id': 'billable_manual',
                            'sequence': sequence_per_invoice_type['billable_manual'],
                            'billed': (timesheet1.unit_amount + timesheet2.unit_amount) * -self.employee_user.hourly_cost +
                                      (foreign_timesheet1.unit_amount + foreign_timesheet2.unit_amount) * -foreign_employee.hourly_cost * 0.2,
                            'to_bill': 0.0,
                        },
                        {
                            'id': 'non_billable',
                            'sequence': sequence_per_invoice_type['non_billable'],
                            'billed': foreign_timesheet3.unit_amount * -foreign_employee_2.hourly_cost * 0.2,
                            'to_bill': 0.0,
                        },
                    ],
                    'total': {
                        'to_bill': 0.0,
                        'billed': -100 + (timesheet1.unit_amount + timesheet2.unit_amount) * -self.employee_user.hourly_cost +
                                  (foreign_timesheet1.unit_amount + foreign_timesheet2.unit_amount) * -foreign_employee.hourly_cost * 0.2 +
                                  foreign_timesheet3.unit_amount * -foreign_employee_2.hourly_cost * 0.2
                    },
                },
            }
        )

        # Create a 3rd timesheet and manually update it.
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
                    'data': [{'id': 'other_revenues', 'sequence': sequence_per_invoice_type['other_revenues'], 'invoiced': 100.0, 'to_invoice': 0.0}],
                    'total': {'invoiced': 100.0, 'to_invoice': 0.0},
                },
                'costs': {
                    'data': [
                        {'id': 'other_costs', 'sequence': sequence_per_invoice_type['other_costs'], 'billed': -100.0, 'to_bill': 0.0},
                        {
                            'id': 'billable_manual',
                            'sequence': sequence_per_invoice_type['billable_manual'],
                            'billed': (timesheet1.unit_amount + timesheet2.unit_amount) * -self.employee_user.hourly_cost +
                                      (foreign_timesheet1.unit_amount + foreign_timesheet2.unit_amount) * -foreign_employee.hourly_cost * 0.2,
                            'to_bill': 0.0,
                        },
                        {
                            'id': 'non_billable',
                            'sequence': sequence_per_invoice_type['non_billable'],
                            'billed': foreign_timesheet3.unit_amount * -foreign_employee_2.hourly_cost * 0.2 + timesheet3.unit_amount * -self.employee_manager.hourly_cost,
                            'to_bill': 0.0,
                        },
                    ],
                    'total': {
                        'to_bill': 0.0,
                        'billed': -100 + (timesheet1.unit_amount + timesheet2.unit_amount) * -self.employee_user.hourly_cost +
                                  (foreign_timesheet1.unit_amount + foreign_timesheet2.unit_amount) * -foreign_employee.hourly_cost * 0.2 +
                                  foreign_timesheet3.unit_amount * -foreign_employee_2.hourly_cost * 0.2 + timesheet3.unit_amount * -self.employee_manager.hourly_cost
                    },
                },
            }
        )

        # Create a new foreign sol, and link this sol to the so_line of the task.
        foreign_delivery_timesheet_order_line = SaleOrderLineForeign.create({
            'product_id': self.product_delivery_timesheet1.id,
            'product_uom_qty': 5,
        })
        self.task.write({'sale_line_id': foreign_delivery_timesheet_order_line.id})
        billable_timesheets = timesheet1 + timesheet2 + foreign_timesheet1 + foreign_timesheet2
        self.assertEqual(billable_timesheets.so_line, foreign_delivery_timesheet_order_line, 'The SOL of the timesheets should be the one of the task.')
        self.assertEqual(foreign_delivery_timesheet_order_line.qty_delivered, timesheet1.unit_amount + timesheet2.unit_amount + foreign_timesheet1.unit_amount + foreign_timesheet2.unit_amount,
                         'Since the product type of the SOL is "delivered on TS", the qty_delivered of the SOL should be the total of unit amount of the TS.')

        self.assertDictEqual(
            self.project_task_rate._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
                        {'id': 'other_revenues', 'sequence': sequence_per_invoice_type['other_revenues'], 'invoiced': 100.0, 'to_invoice': 0.0},
                        {
                            'id': 'billable_time',
                            'sequence': sequence_per_invoice_type['billable_time'],
                            'to_invoice': foreign_delivery_timesheet_order_line.untaxed_amount_to_invoice * 0.2,
                            'invoiced': 0.0
                        },
                    ],
                    'total': {'invoiced': 100.0, 'to_invoice': foreign_delivery_timesheet_order_line.untaxed_amount_to_invoice * 0.2},
                },
                'costs': {
                    'data': [
                        {'id': 'other_costs', 'sequence': sequence_per_invoice_type['other_costs'], 'billed': -100.0, 'to_bill': 0.0},
                        {
                            'id': 'billable_time',
                            'sequence': sequence_per_invoice_type['billable_time'],
                            'billed': (timesheet1.unit_amount + timesheet2.unit_amount) * -self.employee_user.hourly_cost +
                                      (foreign_timesheet1.unit_amount + foreign_timesheet2.unit_amount) * -foreign_employee.hourly_cost * 0.2,
                            'to_bill': 0.0,
                        },
                        {
                            'id': 'non_billable',
                            'sequence': sequence_per_invoice_type['non_billable'],
                            'billed': foreign_timesheet3.unit_amount * -foreign_employee_2.hourly_cost * 0.2 + timesheet3.unit_amount * -self.employee_manager.hourly_cost,
                            'to_bill': 0.0,
                        },
                    ],
                    'total': {
                        'to_bill': 0.0,
                        'billed': -100 + (timesheet1.unit_amount + timesheet2.unit_amount) * -self.employee_user.hourly_cost +
                                  (foreign_timesheet1.unit_amount + foreign_timesheet2.unit_amount) * -foreign_employee.hourly_cost * 0.2 +
                                  foreign_timesheet3.unit_amount * -foreign_employee_2.hourly_cost * 0.2 + timesheet3.unit_amount * -self.employee_manager.hourly_cost
                    },
                },
            }
        )
        # Create a new task in the project, link to it a new SO form the main company SO with a delivery timesheet product.
        delivery_timesheet_order_line = SaleOrderLine.create({
            'product_id': self.product_delivery_timesheet1.id,
            'product_uom_qty': 5,
        })
        task_2 = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Task 2',
            'project_id': self.project_task_rate.id,
            'sale_line_id': delivery_timesheet_order_line.id,
        })
        task2_timesheet = Timesheet.with_context(default_task_id=task_2.id).create({
            'name': '/',
            'project_id': self.project_task_rate.id,
            'employee_id': self.employee_user.id,
            'unit_amount': 1,
        })
        self.assertNotEqual(delivery_timesheet_order_line.untaxed_amount_to_invoice, 0.0)
        self.assertDictEqual(
            self.project_task_rate._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
                        {'id': 'other_revenues', 'sequence': sequence_per_invoice_type['other_revenues'],
                         'invoiced': 100.0, 'to_invoice': 0.0},
                        {
                            'id': 'billable_time',
                            'sequence': sequence_per_invoice_type['billable_time'],
                            'to_invoice': delivery_timesheet_order_line.untaxed_amount_to_invoice + foreign_delivery_timesheet_order_line.untaxed_amount_to_invoice * 0.2,
                            'invoiced': 0.0
                        },
                    ],
                    'total': {'invoiced': 100.0, 'to_invoice': foreign_delivery_timesheet_order_line.untaxed_amount_to_invoice * 0.2 + delivery_timesheet_order_line.untaxed_amount_to_invoice},
                },
                'costs': {
                    'data': [
                        {'id': 'other_costs', 'sequence': sequence_per_invoice_type['other_costs'], 'billed': -100.0,
                         'to_bill': 0.0},
                        {
                            'id': 'billable_time',
                            'sequence': sequence_per_invoice_type['billable_time'],
                            'billed': (timesheet1.unit_amount + timesheet2.unit_amount + task2_timesheet.unit_amount) * -self.employee_user.hourly_cost +
                                      (foreign_timesheet1.unit_amount + foreign_timesheet2.unit_amount) * -foreign_employee.hourly_cost * 0.2,
                            'to_bill': 0.0,
                        },
                        {
                            'id': 'non_billable',
                            'sequence': sequence_per_invoice_type['non_billable'],
                            'billed': foreign_timesheet3.unit_amount * -foreign_employee_2.hourly_cost * 0.2 + timesheet3.unit_amount * -self.employee_manager.hourly_cost,
                            'to_bill': 0.0,
                        },
                    ],
                    'total': {
                        'to_bill': 0.0,
                        'billed': -100 + (timesheet1.unit_amount + timesheet2.unit_amount + task2_timesheet.unit_amount) * -self.employee_user.hourly_cost +
                                  (foreign_timesheet1.unit_amount + foreign_timesheet2.unit_amount) * -foreign_employee.hourly_cost * 0.2 +
                                  foreign_timesheet3.unit_amount * -foreign_employee_2.hourly_cost * 0.2 + timesheet3.unit_amount * -self.employee_manager.hourly_cost
                    },
                },
            }
        )
        # Create a SOL in the foreign SO with a milestone service product.
        milestone_foreign_order_line = SaleOrderLineForeign.create({
            'product_id': self.product_milestone.id,
            'product_uom_qty': 1,
        })
        task2_foreign = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test',
            'project_id': self.project_task_rate.id,
            'sale_line_id': milestone_foreign_order_line.id,
        })
        task2_foreign_timesheet = Timesheet.with_context(default_task_id=task2_foreign.id).create({
            'name': '/',
            'project_id': self.project_task_rate.id,
            'employee_id': foreign_employee.id,
            'unit_amount': 1,
        })
        self.assertEqual(task2_foreign_timesheet.so_line, milestone_foreign_order_line)
        profitability_items = self.project_task_rate._get_profitability_items(False)
        self.assertFalse([data for data in profitability_items['revenues']['data'] if data['id'] == 'billable_milestones'])
        self.assertDictEqual(
            [data for data in profitability_items['costs']['data'] if data['id'] == 'billable_milestones'][0],
            {'id': 'billable_milestones', 'sequence': sequence_per_invoice_type['billable_milestones'], 'to_bill': 0.0, 'billed': task2_foreign_timesheet.amount * 0.2},
        )
        milestone_foreign_order_line.qty_delivered = 1
        profitability_items = self.project_task_rate._get_profitability_items(False)
        self.assertDictEqual(
            [data for data in profitability_items['revenues']['data'] if data['id'] == 'billable_milestones'][0],
            {'id': 'billable_milestones', 'sequence': sequence_per_invoice_type['billable_milestones'],
             'to_invoice': milestone_foreign_order_line.untaxed_amount_to_invoice * 0.2, 'invoiced': 0.0},
        )
        # Create a second timesheet in the new task, with an employee from the main company.
        task2_timesheet = Timesheet.with_context(default_task_id=task2_foreign.id).create({
            'name': '/',
            'project_id': self.project_task_rate.id,
            'employee_id': self.employee_user.id,
            'unit_amount': 1,
        })
        profitability_items = self.project_task_rate._get_profitability_items(False)
        self.assertDictEqual(
            [data for data in profitability_items['costs']['data'] if data['id'] == 'billable_milestones'][0],
            {'id': 'billable_milestones', 'sequence': sequence_per_invoice_type['billable_milestones'], 'to_bill': 0.0,
             'billed': task2_timesheet.amount + task2_foreign_timesheet.amount * 0.2},
        )
        milestone_foreign_order_line.qty_delivered = 2
        profitability_items = self.project_task_rate._get_profitability_items(False)
        self.assertDictEqual(
            [data for data in profitability_items['revenues']['data'] if data['id'] == 'billable_milestones'][0],
            {'id': 'billable_milestones', 'sequence': sequence_per_invoice_type['billable_milestones'],
             'to_invoice': milestone_foreign_order_line.untaxed_amount_to_invoice * 0.2, 'invoiced': 0.0},
        )
        # Create a SOL in the foreign SO with a milestone service product.
        milestone_order_line = SaleOrderLine.create({
            'product_id': self.product_milestone.id,
            'product_uom_qty': 1,
        })
        task3_milestone = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Task 3',
            'project_id': self.project_task_rate.id,
            'sale_line_id': milestone_order_line.id,
        })
        task3_timesheet = Timesheet.with_context(default_task_id=task3_milestone.id).create({
            'name': '/',
            'project_id': self.project_task_rate.id,
            'employee_id': self.employee_user.id,
            'unit_amount': 1,
        })
        profitability_items = self.project_task_rate._get_profitability_items(False)
        self.assertDictEqual(
            [data for data in profitability_items['costs']['data'] if data['id'] == 'billable_milestones'][0],
            {'id': 'billable_milestones', 'sequence': sequence_per_invoice_type['billable_milestones'], 'to_bill': 0.0,
             'billed': task2_timesheet.amount + task2_foreign_timesheet.amount * 0.2 + task3_timesheet.amount},
        )
        milestone_order_line.qty_delivered = 1
        profitability_items = self.project_task_rate._get_profitability_items(False)
        self.assertDictEqual(
            [data for data in profitability_items['revenues']['data'] if data['id'] == 'billable_milestones'][0],
            {'id': 'billable_milestones', 'sequence': sequence_per_invoice_type['billable_milestones'],
             'to_invoice': milestone_foreign_order_line.untaxed_amount_to_invoice * 0.2 + milestone_order_line.untaxed_amount_to_invoice, 'invoiced': 0.0},
        )

        # Cancel the milestone timesheets
        task2_timesheet.unlink()
        task2_foreign_timesheet.unlink()
        task3_timesheet.unlink()
        profitability_items = self.project_task_rate._get_profitability_items(False)
        self.assertFalse([data for data in profitability_items['revenues']['data'] if data['id'] == 'billable_milestones'])
        self.assertFalse([data for data in profitability_items['costs']['data'] if data['id'] == 'billable_milestones'])
