# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
import time


class TestHrTimesheetSheet(TransactionCase):
    """Test for hr_timesheet_sheet.sheet"""

    def setUp(self):
        super(TestHrTimesheetSheet, self).setUp()
        self.attendance = self.env['hr.attendance']
        self.timesheet_sheet = self.env['hr_timesheet_sheet.sheet']
        self.test_employee = self.browse_ref('hr.employee_qdp')
        self.company = self.browse_ref('base.main_company')
        self.company.timesheet_max_difference = 1.00

    def test_hr_timesheet_sheet(self):

        # I create a timesheet for employee "Gilles Gravie".
        self.test_timesheet_sheet = self.timesheet_sheet.create({
            'date_from': time.strftime('%Y-%m-11'),
            'date_to': time.strftime('%Y-%m-17'),
            'name': 'Gilles Gravie',
            'state': 'new',
            'user_id': self.browse_ref('base.user_demo').id,
            'employee_id': self.test_employee.id,
        })

        # I check Gilles in at around 9:00 and out at 17:30
        self.attendance.create({
            'employee_id': self.test_employee.id,
            'check_in': time.strftime('%Y-%m-11 09:12:37'),
            'check_out': time.strftime('%Y-%m-11 17:30:00'),
        })

        # I add 6 hours of work to Gilles' timesheet
        self.test_timesheet_sheet.write({'timesheet_ids': [(0, 0, {
            'project_id': self.browse_ref('project.project_project_2').id,
            'date': time.strftime('%Y-%m-11'),
            'name': 'Develop yaml for hr module(1)',
            'user_id': self.browse_ref('base.user_demo').id,
            'unit_amount': 6.00,
            'amount': -90.00,
            'product_id': self.browse_ref('product.product_product_1').id,
        })]})

        # I confirm Gilles' timesheet with over 1 hour difference
        # in attendance and actual worked hours
        try:
            self.test_timesheet_sheet.action_timesheet_confirm()
        except Exception:
            pass

        # I add another 2 hours of work to Gilles' timesheet
        self.test_timesheet_sheet.write({'timesheet_ids': [(0, 0, {
            'project_id': self.browse_ref('project.project_project_2').id,
            'date': time.strftime('%Y-%m-11'),
            'name': 'Develop yaml for hr module(2)',
            'user_id': self.browse_ref('base.user_demo').id,
            'unit_amount': 2.00,
            'amount': -90.00,
            'product_id': self.browse_ref('product.product_product_1').id,
        })]})
        # I invalidate the cache, otherwise total_timesheet and total_difference doesn't get updated... /this is a disgrace/
        self.test_timesheet_sheet.invalidate_cache(['total_attendance', 'total_timesheet', 'total_difference'])

        # I confirm Gilles' timesheet with less than 1 hour difference
        # in attendance and actual worked hours
        self.test_timesheet_sheet.action_timesheet_confirm()

        # I check the state is confirmed
        assert self.test_timesheet_sheet.state == 'confirm'

        # the manager accepts the timesheet
        self.test_timesheet_sheet.write({'state': 'done'})

        # I check the state is indeed done
        assert self.test_timesheet_sheet.state == 'done'
