# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged('post_install', '-at_install')
class TestTaskDisplayNameParent(BaseCommon):
    # the tests run as a timesheet user, the records are set up as admin
    _test_user_groups = ('hr_timesheet.group_hr_timesheet_user',)

    @classmethod
    def get_default_groups(cls):
        return super().get_default_groups() | cls.quick_ref('project.group_project_manager')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # team-only project the test user is not a member of
        cls.private_project = cls.env['project.project'].create({
            'name': 'Private Project',
            'privacy_visibility': 'followers',
            'allow_timesheets': True,
        })
        cls.public_project = cls.env['project.project'].create({
            'name': 'Public Project',
            'privacy_visibility': 'employees',
            'allow_timesheets': True,
        })
        cls.parent = cls.env['project.task'].create({
            'name': 'Parent Task',
            'project_id': cls.public_project.id,
        })
        cls.subtask = cls.env['project.task'].create({
            'name': 'Sub Task',
            'project_id': cls.public_project.id,
            'parent_id': cls.parent.id,
        })
        # parent hidden from the test user, subtask visible
        cls.hidden_parent = cls.env['project.task'].create({
            'name': 'Hidden Parent',
            'project_id': cls.private_project.id,
        })
        cls.visible_subtask = cls.env['project.task'].create({
            'name': 'Visible Sub Task',
            'project_id': cls.public_project.id,
            'parent_id': cls.hidden_parent.id,
        })

    def _display_name(self, task, formatted=False):
        return task.with_context(
            hr_timesheet_display_remaining_hours=True,
            formatted_display_name=formatted,
        ).display_name

    def test_parent_in_dropdown(self):
        self.assertEqual(self._display_name(self.subtask, formatted=True), "Sub Task \t --Parent Task--")

    def test_parent_outside_dropdown(self):
        self.assertEqual(self._display_name(self.subtask), "Sub Task Parent Task")

    def test_parent_after_remaining_hours(self):
        self.subtask.sudo().allocated_hours = 5
        name = self._display_name(self.subtask, formatted=True)
        self.assertTrue(name.startswith("Sub Task \t --"), "remaining hours come first")
        self.assertTrue(name.endswith("-- \t --Parent Task--"), "parent comes last")

    def test_task_without_parent(self):
        self.assertEqual(self._display_name(self.parent, formatted=True), "Parent Task")

    def test_parent_hidden_when_not_readable(self):
        # precondition: the user can see the subtask but not its parent
        self.assertTrue(self.visible_subtask.has_access('read'))
        self.assertFalse(self.hidden_parent.has_access('read'))
        # no AccessError, and the parent name does not leak
        self.assertEqual(self._display_name(self.visible_subtask, formatted=True), "Visible Sub Task")
        self.assertEqual(self._display_name(self.visible_subtask), "Visible Sub Task")
