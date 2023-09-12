# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import HttpCase, tagged, users


@tagged('post_install', '-at_install')
class TestTodoUi(HttpCase):

    @users('admin')
    def test_tour_project_task_activities_split(self):
        """ Activities linked to project.task records can appear either in the
            'Task', either in the 'To-Do' category, depending on wether they are
            linked to a project or not. This test ensures that:
                - activities linked to records with no project_id set and no
                  parent are listed in the 'To-Do' category
                - activities linked to records with either project_id set or
                  linked to a parent task are listed in the 'Task' category
        """
        project = self.env['project.project'].create([{'name': 'Test project'}])
        stage = self.env['project.task.type'].create([{
            'name': 'Test Stage',
            'project_ids': project.ids,
        }])
        private_task, task = self.env['project.task'].create([{
            'name': 'New To-Do!',
            'project_id': False,
        }, {
            'name': 'New Task!',
            'project_id': project.id,
            'stage_id': stage.id,
            'child_ids': [
                Command.create({
                    'name': 'New Sub-Task!',
                    'project_id': False,
                }),
            ]
        }])

        subtask = task.child_ids
        task.activity_schedule(act_type_xmlid='mail.mail_activity_data_todo')
        subtask.activity_schedule(act_type_xmlid='mail.mail_activity_data_todo')
        private_task.activity_schedule(act_type_xmlid='mail.mail_activity_data_todo')

        # Ensure that all activities appear in the systray under the good category
        # name and that clicking on this category opens the correct view where only
        # records of this category are listed.
        self.start_tour("/web", 'project_task_activities_split', login="admin")
