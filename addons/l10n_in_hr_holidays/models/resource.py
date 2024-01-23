# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import time
from odoo import models

class CalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    def generate_public_leaves(self):
        work_entry_type_id = self.env.ref("l10n_in_hr_payroll.work_entry_type_bank_holiday_in")
        public_leaves = [
            {"name":"Independence Day", "date_from":time.strftime('%Y-08-15 02:30:00'), "date_to": time.strftime('%Y-08-15 18:29:59'), "work_entry_type_id":work_entry_type_id.id},
            {"name":"Republic Day", "date_from":time.strftime('%Y-01-26 02:30:00'), "date_to": time.strftime('%Y-01-26 18:29:59'), "work_entry_type_id":work_entry_type_id.id},
            {"name":"Gandhi Jayanti", "date_from":time.strftime('%Y-10-02 02:30:00'), "date_to": time.strftime('%Y-10-02 18:29:59'), "work_entry_type_id":work_entry_type_id.id},
            {"name":"Makar Sakranti", "date_from":time.strftime('%Y-01-14 02:30:00'), "date_to": time.strftime('%Y-01-14 18:29:59'), "work_entry_type_id":work_entry_type_id.id},
        ]

        #  Hack: We can't use "name" to check(there can be mispelling) if public_leaves exists or not, so using date_from to check it.
        data_start, data_end = time.strftime('%Y-01-01'), time.strftime('%Y-12-31')
        all_public_leaves = self.env['hr.employee']._get_public_holidays(data_start, data_end)
        if all_public_leaves:
            #  if we add anything in public_leaves we must add that leave's date to expected_public_leaves_dates
            expected_public_leaves_dates = [time.strftime('%Y-08-15'), time.strftime('%Y-01-26'), time.strftime('%Y-10-02'), time.strftime('%Y-01-14')]
            for leave in all_public_leaves:
                if leave.date_from.date().strftime('%Y-%m-%d') in expected_public_leaves_dates:
                    public_leaves = [public_leave for public_leave in public_leaves
                                    if datetime.strptime(public_leave['date_from'], '%Y-%m-%d %H:%M:%S').date() != leave.date_from.date()]

        if public_leaves:
            companies = self.env.company.search([])
            ind_companies = companies.filtered(lambda x: x.country_code == "IN")
            for ind_company in ind_companies:
                self.env["resource.calendar.leaves"].with_company(ind_company).create(public_leaves)
