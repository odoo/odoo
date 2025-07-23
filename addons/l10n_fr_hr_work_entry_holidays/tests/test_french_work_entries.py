# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import time

from datetime import datetime
from odoo.tests import Form
from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)

@tagged('post_install_l10n', 'post_install', '-at_install', 'french_work_entries')
class TestFrenchWorkEntries(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        country_fr = cls.env.ref('base.fr')
        cls.company = cls.env['res.company'].create({
            'name': 'French Company',
            'country_id': country_fr.id,
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Louis',
            'gender': 'other',
            'birthday': '1973-03-29',
            'country_id': country_fr.id,
            'company_id': cls.company.id,
        })

        cls.employee_contract = cls.env['hr.contract'].create({
            'date_start': '2020-01-01',
            'date_end': '2023-01-01',
            'name': 'Louis\'s contract',
            'wage': 2,
            'employee_id': cls.employee.id,
            'company_id': cls.company.id,
        })

        cls.time_off_type = cls.env['hr.leave.type'].create({
            'name': 'Time Off',
            'requires_allocation': False,
        })
        cls.company.write({
            'l10n_fr_reference_leave_type': cls.time_off_type.id,
        })

    def test_fill_gaps(self):
        company_calendar = self.env['resource.calendar'].create({
            'name': 'Company Calendar',
        })
        employee_calendar = self.env['resource.calendar'].create({
            'name': 'Employee Calendar',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ],
        })
        self.company.resource_calendar_id = company_calendar
        self.employee.resource_calendar_id = employee_calendar
        self.employee_contract.resource_calendar_id = employee_calendar

        # Get the create values for a week of work entries, it should only give us 4 entries ((am+pm) * 2)
        work_entry_create_vals = self.employee_contract._get_contract_work_entries_values(datetime(2021, 9, 6), datetime(2021, 9, 10, 23, 59, 59))
        self.assertEqual(len(work_entry_create_vals), 4, 'Should have generated 4 work entries.')

        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'request_date_from': '2021-09-06',
            'request_date_to': '2021-09-08',  # This should fill the gap up to the 10th
        })
        leave.action_approve()

        # Since the gaps have been filled, we should now get 10 work entries
        with self.assertQueryCount(45):
            start_time = time.time()
            work_entry_create_vals = self.employee_contract._get_contract_work_entries_values(datetime(2021, 9, 6), datetime(2021, 9, 10, 23, 59, 59))
            # --- 0.11486363410949707 seconds ---
            _logger.info("Get Contract Work Entries: --- %s seconds ---", time.time() - start_time)
        self.assertEqual(len(work_entry_create_vals), 10, 'Should have generated 10 work entries.')

        # Make sure that the gap filling does not go past the requested date
        work_entry_create_vals = self.employee_contract._get_contract_work_entries_values(datetime(2021, 9, 6), datetime(2021, 9, 9, 23, 59, 59))
        self.assertEqual(len(work_entry_create_vals), 8, 'Should have generated 8 work entries.')

    def test_create_work_entry_with_french_company(self):
        self.employee_contract.write({'state': 'open'})
        with Form(self.env['hr.work.entry'].with_company(self.company)) as work_entry_form:
            work_entry_form.employee_id = self.employee
            work_entry_form.date_start = '2020-01-01 08:00:00'
            work_entry_form.date_stop = '2020-01-01 17:00:00'
            work_entry = work_entry_form.save()
        self.assertEqual(work_entry.duration, 9)
