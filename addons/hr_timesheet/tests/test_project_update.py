# -*- coding: utf-8 -*-

from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.project.tests.test_project_update_flow import TestProjectUpdate

@tagged('-at_install', 'post_install')
class TestProjectUpdateHrTimesheet(TestProjectUpdate):

    def _create_timesheet(self):
        self.employee = self.env['hr.employee'].create({
            'name': "Randy Heart",
            'company_id': self.env.company.id
        })
        self.timesheet = self.env['account.analytic.line'].create({
            'project_id': self.project_pigs.id,
            'task_id': self.task_1.id,
            'name': 'my first timesheet',
            'unit_amount': 4,
            'employee_id': self.employee.id,
        })

    def test_project_update_form_people(self):
        self._create_timesheet()
        try:
            with Form(self.env['project.update'].with_context({'default_project_id': self.project_pigs.id})) as update_form:
                update_form.name = "Test"
                update_form.progress = 65
            update = update_form.save()
        except Exception as e:
            raise AssertionError("Error raised unexpectedly while filling the project update form ! Exception : " + e.args[0])

        self.assertTrue("People" in update.description, "The description should contain 'People'.")

    def test_project_update_form_no_people(self):
        try:
            with Form(self.env['project.update'].with_context({'default_project_id': self.project_pigs.id})) as update_form:
                update_form.name = "Test"
                update_form.progress = 65
            update = update_form.save()
        except Exception as e:
            raise AssertionError("Error raised unexpectedly while filling the project update form ! Exception : " + e.args[0])

        self.assertFalse("People" in update.description, "The description should not contain 'People'.")

    def test_project_update_description_people(self):
        self._create_timesheet()
        template_values = self.env['project.update']._get_template_values(self.project_pigs)

        self.assertEqual(template_values['people']['uom'], "hours", "The timesheet uom is well given to template")
        self.assertTrue(template_values['people']['is_uom_hour'], "Company default timesheet uom is hours")
        self.assertEqual(len(template_values['people']['activities']), 1, "The number of recorded timesheet activities is 1")
        self.assertEqual(template_values['people']['activities'][0]['name'], "Randy Heart", "The number of recorded timesheet activities is 1")
