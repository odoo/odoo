# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo import Command


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_project_tour(self):
        self.start_tour("/web", 'project_tour', login="admin")

    def test_project_task_history(self):
        """This tour will check that the history works properly."""
        project = self.env['project.project'].create({
            'name': 'Test History Project',
            'type_ids': [Command.create({'name': 'To Do'})],
        })

        self.env['project.task'].create({
            'name': 'Test History Task',
            'stage_id': project.type_ids[0].id,
            'project_id': project.id,
        })

        self.start_tour('/web', 'project_task_history_tour', login='admin')
