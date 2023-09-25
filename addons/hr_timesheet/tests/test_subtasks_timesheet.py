# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet

class TestSubtasksTimesheet(TestCommonTimesheet):

    @classmethod
    def setUpClass(cls):
        super(TestSubtasksTimesheet, cls).setUpClass()

        cls.projects = cls.env['project.project'].create([{
            'name': 'Project %s' % i,
            'allocated_hours': 20,
        } for i in range(3)])
        cls.tasks = cls.env['project.task'].create([{
            'name': 'Task %s (%s)' % (i, project.name),
            'project_id': project.id,
            'allocated_hours': 10,
        } for project in cls.projects for i in range(2)])
        cls.subtasks = cls.env['project.task'].create([
            {
                'name': 'Subtask 0 (linked to and in Project 0)',
                'parent_id': cls.tasks[0].id,
                'project_id': cls.projects[0].id,
            }, {
                'name': 'Subtask 1 (linked to but out of Project 0, in Project 1)',
                'parent_id': cls.tasks[0].id,
                'project_id': cls.projects[1].id,
            }, {
                'name': 'Subtask 2 (linked to but out of Project 0, in Project 1)',
                'parent_id': cls.tasks[1].id,
                'project_id': cls.projects[1].id,
            }
        ])
        cls.subsubtasks = cls.env['project.task'].create([
            {
                'name': 'Subsubtask 0 (linked to but out of Project 0, in Project 2)',
                'parent_id': cls.subtasks[0].id,
                'project_id': cls.projects[2].id,
            }, {
                'name': 'Subsubtask 1 (linked to and in Project 0)',
                'parent_id': cls.subtasks[0].id,
                'project_id': cls.projects[0].id,
            }, {
                'name': 'Subsubtask 2 (linked to and in Project 0, linked to but out of project 1)',
                'parent_id': cls.subtasks[1].id,
                'project_id': cls.projects[0].id,
            }, {
                'name': 'Subsubtask 3 (linked to but out of Project 0 and 1, in Project 2)',
                'parent_id': cls.subtasks[2].id,
                'project_id': cls.projects[2].id,
            }
        ])

    def test_project_get_outer_subtasks(self):
        
        result = self.projects._get_outer_subtasks_by_project_id()

        self.assertEqual(set(result.keys()), set(self.projects[0:2].ids),
                        'All project with outer subtasks should be listed in the results')
        self.assertEqual(len(result[self.projects[0].id]), 4,
                         'Exactly 4 outer subtasks should be listed for Project 0')
        self.assertEqual(set(result[self.projects[0].id]), set((self.subtasks[1:3] + self.subsubtasks[0] + self.subsubtasks[3]).ids),
                         'Outer subtasks listed for Project 0 are incorrect')
        self.assertEqual(len(result[self.projects[1].id]), 2,
                         'Exactly two outer subtasks should be listed for Project 1')
        self.assertEqual(set(result[self.projects[1].id]), set((self.subsubtasks[2:4]).ids),
                         'Outer subtasks listed for Project 1 are incorrect')

    def test_compute_total_timesheet_time(self):
        """total_timesheet_time field of project.project should take into account the
           time spend on all subtasks, even if they do not belong to the project.
        """

        # 1. Creating timesheets
        self.env['account.analytic.line'].create([
            {
                'project_id': self.tasks[0].project_id.id,
                'task_id': self.tasks[0].id,
                'name': 'a timesheet for employee 1 on project 0',
                'unit_amount': 1,
                'employee_id': self.empl_employee.id,
            }, {
                'project_id': self.tasks[1].project_id.id,
                'task_id': self.tasks[1].id,
                'name': 'a timesheet for employee 1 on project 0',
                'unit_amount': 1,
                'employee_id': self.empl_employee.id,
            }, {
                'project_id': self.subtasks[0].project_id.id,
                'task_id': self.subtasks[0].id,
                'name': 'a timesheet for employee 1 on project 0',
                'unit_amount': 1,
                'employee_id': self.empl_employee.id,
            }, {
                'project_id': self.subtasks[1].project_id.id,
                'task_id': self.subtasks[1].id,
                'name': 'a timesheet for employee 1 on projects 0 and 1',
                'unit_amount': 1,
                'employee_id': self.empl_employee.id,
            }, {
                'project_id': self.subtasks[2].project_id.id,
                'task_id': self.subtasks[2].id,
                'name': 'a timesheet for employee 1 on projects 0 and 1',
                'unit_amount': 1,
                'employee_id': self.empl_employee.id,
            }, {
                'project_id': self.subsubtasks[0].project_id.id,
                'task_id': self.subsubtasks[0].id,
                'name': 'a timesheet for employee 1 on projects 0 and 2',
                'unit_amount': 1,
                'employee_id': self.empl_employee.id,
            }, {
                'project_id': self.subsubtasks[1].project_id.id,
                'task_id': self.subsubtasks[1].id,
                'name': 'a timesheet for employee 1 on project 0',
                'unit_amount': 1,
                'employee_id': self.empl_employee.id,
            }, {
                'project_id': self.subsubtasks[2].project_id.id,
                'task_id': self.subsubtasks[2].id,
                'name': 'a timesheet for employee 1 on projects 0 and 1',
                'unit_amount': 1,
                'employee_id': self.empl_employee.id,
            }, {
                'project_id': self.subsubtasks[3].project_id.id,
                'task_id': self.subsubtasks[3].id,
                'name': 'a timesheet for employee 1 on projects 0, 1 and 2',
                'unit_amount': 1,
                'employee_id': self.empl_employee.id,
            }
        ])

        # 2. Total timesheet time should be:
        #       - For project 0: 9 hours
        #       - For project 1: 4 hours
        #       - For project 2: 2 hours

        self.env.invalidate_all()
        self.env.registry.clear_cache()
        # Performance is critical for this method, and in particular the query to get all subtasks should not be repeated for each project
        with self.assertQueryCount(10): 
            self.assertEqual(self.projects[0].total_timesheet_time, 9,
                             "Total timesheet time spent on Project 0 and its subtasks is incorrect")
        self.assertEqual(self.projects[1].total_timesheet_time, 4,
                         "Total timesheet time spent on Project 1 and its subtasks is incorrect")
        self.assertEqual(self.projects[2].total_timesheet_time, 2,
                         "Total timesheet time spent on Project 2 and its subtasks is incorrect")

        # 3. Remaining time should be:
        #       - For project 0: 11 hours
        #       - For project 1: 16 hours
        #       - For project 2: 18 hours

        self.env.invalidate_all()
        self.env.registry.clear_cache()
        # Performance is critical for this method, and in particular the query to get all subtasks should not be repeated for each project
        with self.assertQueryCount(11): 
            self.assertEqual(self.projects[0].remaining_hours, 11,
                             "Total timesheet time spent on Project 0 and its subtasks is incorrect")
        self.assertEqual(self.projects[1].remaining_hours, 16,
                         "Total timesheet time spent on Project 1 and its subtasks is incorrect")
        self.assertEqual(self.projects[2].remaining_hours, 18,
                         "Total timesheet time spent on Project 2 and its subtasks is incorrect")
