# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet

class TestPerformanceTimesheet(TestCommonTimesheet):

    def test_timesheet_preprocess(self):
        projects = self.env['project.project'].create([{'name': 'Project %s' % i} for i in range(6)])
        tasks = self.env['project.task'].create([{
            'name': 'Task %s (%s)' % (i, project.name),
            'project_id': project.id,
        } for i in range(17) for project in projects])
        self.env.invalidate_all()
        self.env.registry.clear_cache()
        with self.assertQueryCount(5):
            self.env['account.analytic.line']._timesheet_preprocess([
                {'task_id': task.id} for task in tasks for _i in range(10)
            ])
