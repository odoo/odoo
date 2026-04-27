# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import datetime
from freezegun import freeze_time

from odoo import fields
from odoo.tests import tagged
from odoo.exceptions import UserError

from .common import TestCommonForecast


@tagged('-at_install', 'post_install')
class TestForecastCreationAndEditing(TestCommonForecast):

    @classmethod
    def setUpClass(cls):
        super(TestForecastCreationAndEditing, cls).setUpClass()
        cls.classPatch(cls.env.cr, 'now', fields.Datetime.now)
        with freeze_time('2019-1-1'):
            cls.setUpEmployees()
            cls.setUpProjects()

        # planning_shift on one day (planning mode)
        cls.slot = cls.env['planning.slot'].create({
            'project_id': cls.project_opera.id,
            'resource_id': cls.employee_bert.resource_id.id,
            'start_datetime': datetime(2019, 6, 6, 8, 0, 0),  # 6/6/2019 is a tuesday, so a working day
            'end_datetime': datetime(2019, 6, 6, 17, 0, 0),
        })

    def test_creating_a_planning_shift_allocated_hours_are_correct(self):
        self.assertEqual(self.slot.allocated_hours, 8.0, 'resource hours should be a full workday')

        self.slot.write({'allocated_percentage': 50})
        self.assertEqual(self.slot.allocated_hours, 4.0, 'resource hours should be a half duration')

        # self.slot on non working days
        values = {
            'allocated_percentage': 100,
            'start_datetime': datetime(2019, 6, 2, 8, 0, 0),  # sunday morning
            'end_datetime': datetime(2019, 6, 2, 17, 0, 0)  # sunday evening, same sunday, so employee is not working
        }
        self.slot.write(values)

        self.assertEqual(self.slot.allocated_hours, 0, 'resource hours should be a full day working hours')

        # self.slot on multiple days (forecast mode)
        values = {
            'allocated_percentage': 100,   # full week
            'start_datetime': datetime(2019, 6, 3, 0, 0, 0),  # 6/3/2019 is a monday
            'end_datetime': datetime(2019, 6, 8, 23, 59, 0)  # 6/8/2019 is a sunday, so we have a full week
        }
        self.slot.write(values)

        self.assertEqual(self.slot.allocated_hours, 40, 'resource hours should be a full week\'s available hours')

    def test_creating_a_planning_shift_with_flexible_hours_allocated_hours_are_correct(self):
        self.employee_bert.resource_id.calendar_id.flexible_hours = True
        self.assertEqual(self.slot.allocated_hours, 8.0, 'resource hours should be a full workday')

        self.slot.write({'allocated_percentage': 50})
        self.assertEqual(self.slot.allocated_hours, 4.0, 'resource hours should be a half duration')

        # self.slot on non working days
        values = {
            'allocated_percentage': 100,
            'start_datetime': datetime(2019, 6, 2, 8, 0, 0),  # sunday morning
            'end_datetime': datetime(2019, 6, 2, 17, 0, 0)  # sunday evening, same sunday, so employee is not working
        }
        self.slot.write(values)

        self.assertEqual(self.slot.allocated_hours, 8, 'resource hours should be a full day working hours')

        # self.slot on multiple days (forecast mode)
        values = {
            'allocated_percentage': 100,   # full week
            'start_datetime': datetime(2019, 6, 3, 0, 0, 0),  # 6/3/2019 is a monday
            'end_datetime': datetime(2019, 6, 8, 23, 0, 0)  # 6/8/2019 is a sunday, so we have a full week
        }
        self.slot.write(values)

        self.assertEqual(self.slot.allocated_hours, 8 * 6, 'allocated hours should be equal to the real period since the resource has a flexible hours.')

    @freeze_time("2023-11-20")
    def test_shift_creation_from_project(self):
        self.env.user.tz = 'Asia/Kolkata'
        self.env.user.company_id.resource_calendar_id.tz = 'Asia/Kolkata'
        PlanningTemplate = self.env['planning.slot.template']
        Project = self.env['project.project']

        project_a = Project.create({'name': 'project_a'})
        project_b = Project.create({'name': 'project_b'})

        template_a = PlanningTemplate.create({
            'start_time': 8,
            'end_time': 10,
            'duration_days': 1,
            'project_id': project_a.id
        })
        self.assertEqual(template_a.duration_days, 1, "Duration in days should be a 1 day according to resource calendar.")
        self.assertEqual(template_a.end_time, 10.0, "End time should be 2 hours from start hours.")

        template_b = PlanningTemplate.create({
            'start_time': 8,
            'end_time': 12,
            'duration_days': 1,
            'project_id': project_b.id
        })
        slot = self.env['planning.slot'].create({'template_id': template_a.id})
        self.assertEqual(slot.project_id.id, slot.template_autocomplete_ids.mapped('project_id').id, "Project of the slot and shift template should be same.")

        slot.template_id = template_b.id
        self.assertEqual(slot.project_id.id, slot.template_autocomplete_ids.mapped('project_id').id, "Project of the slot and shift template should be same.")

    def test_consistency_change_project_company(self):
        new_company = self.env['res.company'].create({'name': 'New Company'})
        # Check that we cannot change the company of the project as it is already linked to shifts that are in another company
        with self.assertRaises(UserError):
            self.project_opera.company_id = new_company
