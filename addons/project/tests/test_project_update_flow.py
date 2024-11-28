# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import Form, tagged

from odoo.addons.project.tests.test_project_base import TestProjectCommon

@tagged('-at_install', 'post_install')
class TestProjectUpdate(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.config.settings'] \
            .create({'group_project_milestone': True}) \
            .execute()

    def test_project_update_form(self):
        with Form(self.env['project.milestone'].with_context({'default_project_id': self.project_pigs.id})) as milestone_form:
            milestone_form.name = "Test 1"
            milestone_form.deadline = fields.Date.today()

        try:
            with Form(self.env['project.update'].with_context({'default_project_id': self.project_pigs.id})) as update_form:
                update_form.name = "Test"
                update_form.progress = 65
            update = update_form.save()
        except Exception as e:
            raise AssertionError("Error raised unexpectedly while filling the project update form ! Exception : " + e.args[0])

        self.assertEqual(update.user_id, self.env.user, "The author is the user who created the update.")
        self.assertNotEqual(len(update.description), 0, "The description should not be empty.")
        self.assertTrue("Activities" in update.description, "The description should contain 'Activities'.")
        self.assertEqual(update.status, 'on_track', "The status should be the default one.")

        with Form(self.env['project.update'].with_context({'default_project_id': self.project_pigs.id})) as update_form:
            update_form.name = "Test 2"
        update = update_form.save()
        self.assertEqual(update.progress, 65, "The default progress is the one from the previous update by default")

    def test_project_update_description(self):
        with Form(self.env['project.milestone'].with_context({'default_project_id': self.project_pigs.id})) as milestone_form:
            milestone_form.name = "Test 1"
            milestone_form.deadline = fields.Date.today()
        with Form(self.env['project.milestone'].with_context({'default_project_id': self.project_pigs.id})) as milestone_form:
            milestone_form.name = "Test 2"
            milestone_form.deadline = fields.Date.today()
        with Form(self.env['project.milestone'].with_context({'default_project_id': self.project_pigs.id})) as milestone_form:
            milestone_form.name = "Test 3"
            milestone_form.deadline = fields.Date.today() + relativedelta(years=2)

        template_values = self.env['project.update']._get_template_values(self.project_pigs)

        self.assertTrue(template_values['milestones']['show_section'], 'The milestone section should not be visible since the feature is disabled')
        self.assertEqual(len(template_values['milestones']['list']), 2, "Milestone list length should be equal to 2")
        self.assertEqual(len(template_values['milestones']['created']), 3, "Milestone created length tasks should be equal to 3")

        self.project_pigs.write({'allow_milestones': False})

        template_values = self.env['project.update']._get_template_values(self.project_pigs)

        self.assertFalse(template_values['milestones']['show_section'], 'The milestone section should not be visible since the feature is disabled')
        self.assertEqual(len(template_values['milestones']['list']), 0, "Milestone list length should be equal to 0 because the Milestones feature is disabled.")
        self.assertEqual(len(template_values['milestones']['created']), 0, "Milestone created length tasks should be equal to 0 because the Milestones feature is disabled.")

        self.project_pigs.write({'allow_milestones': True})
        self.env['res.config.settings'] \
            .create({'group_project_milestone': False}) \
            .execute()

        template_values = self.env['project.update']._get_template_values(self.project_pigs)

        self.assertFalse(template_values['milestones']['show_section'], 'The milestone section should not be visible since the feature is disabled')
        self.assertEqual(len(template_values['milestones']['list']), 0, "Milestone list length should be equal to 0 because the Milestones feature is disabled.")
        self.assertEqual(len(template_values['milestones']['created']), 0, "Milestone created length tasks should be equal to 0 because the Milestones feature is disabled.")

    def test_project_update_panel(self):
        with Form(self.env['project.milestone'].with_context({'default_project_id': self.project_pigs.id})) as milestone_form:
            milestone_form.name = "Test 1"
            milestone_form.deadline = fields.Date.today() + relativedelta(years=-1)
        with Form(self.env['project.milestone'].with_context({'default_project_id': self.project_pigs.id})) as milestone_form:
            milestone_form.name = "Test 2"
            milestone_form.deadline = fields.Date.today() + relativedelta(years=-1)
            milestone_form.is_reached = True
        with Form(self.env['project.milestone'].with_context({'default_project_id': self.project_pigs.id})) as milestone_form:
            milestone_form.name = "Test 3"
            milestone_form.deadline = fields.Date.today() + relativedelta(years=2)

        panel_data = self.project_pigs.get_panel_data()

        self.assertEqual(len(panel_data['milestones']['data']), 3, "Panel data should contain 'milestone' entry")
        self.assertFalse(panel_data['milestones']['data'][0]['is_deadline_exceeded'], "Milestone is achieved")
        self.assertTrue(panel_data['milestones']['data'][1]['is_deadline_exceeded'], "Milestone is exceeded")
        self.assertTrue(panel_data['milestones']['data'][0]['is_reached'], "Milestone is done")
        self.assertFalse(panel_data['milestones']['data'][1]['is_reached'], "Milestone isn't done")
        # sorting
        self.assertEqual(panel_data['milestones']['data'][0]['name'], "Test 2", "Sorting isn't correct")
        self.assertEqual(panel_data['milestones']['data'][1]['name'], "Test 1", "Sorting isn't correct")
        self.assertEqual(panel_data['milestones']['data'][2]['name'], "Test 3", "Sorting isn't correct")

        # Disable the "Milestones" feature in the project and check the "Milestones" section is not loaded for this project.
        self.project_pigs.write({'allow_milestones': False})
        panel_data = self.project_pigs.get_panel_data()
        self.assertNotIn('milestones', panel_data, 'Since the "Milestones" feature is disabled in this project, the "Milestones" section is not loaded.')

        # Disable globally the Milestones feature and check the Milestones section is not loaded.
        self.project_pigs.write({'allow_milestones': True})
        self.env['res.config.settings'] \
            .create({'group_project_milestone': False}) \
            .execute()
        panel_data = self.project_pigs.get_panel_data()
        self.assertNotIn('milestones', panel_data, 'Since the "Milestones" feature is globally disabled, the "Milestones" section is not loaded.')

    def test_project_update_values(self):
        # Create a project and associated tasks
        project = self.env['project.project'].create({'name': 'Project'})
        task1, task2, task3 = self.env['project.task'].create([
            {'name': 'Task 1', 'project_id': project.id},
            {'name': 'Task 2', 'project_id': project.id},
            {'name': 'Task 3', 'project_id': False},
        ])

        # Function to create a project update and validate counts
        def validate_update(expected_closed_count, expected_percentage):
            with Form(self.env['project.update'].with_context({'default_project_id': project.id})) as update_form:
                update_form.name = "Test"
            update = update_form.save()
            self.assertEqual(update.task_count, project.task_count, "Task count should match project task count")
            self.assertEqual(update.closed_task_count, expected_closed_count, "Closed task count should match")
            self.assertEqual(update.closed_task_percentage, expected_percentage, "Closed task percentage should match")
            return update

        # Initial validation: No tasks are closed
        validate_update(0, 0)

        # Mark task1 as done and validate closed task counts and percentage
        task1.state = '1_done'
        validate_update(1, 50)

        # Mark task2 as canceled and assign task3 to the project, then validate again
        task2.state = '1_canceled'
        task3.project_id = project.id
        validate_update(2, 67)
