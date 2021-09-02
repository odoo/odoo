# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.project.tests.test_project_base import TestProjectCommon

@tagged('-at_install', 'post_install')
class TestProjectUpdate(TestProjectCommon):

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

        self.assertEqual(len(template_values['milestones']['list']), 2, "Milestone list length should be equal to 2")
        self.assertEqual(len(template_values['milestones']['created']), 3, "Milestone created length tasks should be equal to 3")

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
