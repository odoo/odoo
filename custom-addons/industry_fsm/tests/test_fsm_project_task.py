# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.tests import tagged

from .common import TestIndustryFsmCommon

@tagged('post_install', '-at_install')
class TestAutoCreateFsmProject(TestIndustryFsmCommon):

    def test_default_project_fsm_subtasks(self):
        _, fsm_project_B = self.env['project.project'].create([
            {
                'name': 'Field Service A',
                'is_fsm': True,
                'company_id': self.env.company.id,
                'allow_timesheets': True,
                'sequence': 100,
            },
            {
                'name': 'Field Service B',
                'is_fsm': True,
                'company_id': self.env.company.id,
                'allow_timesheets': True,
                'sequence': 200,
            }
        ])
        task = self.env['project.task'].create({
            'name': 'Fsm task',
            'project_id': fsm_project_B.id,
            'partner_id': self.partner.id,
        })
        subtask = self.env['project.task'].with_context(
                fsm_mode=True,
                default_parent_id=task.id,
                default_project_id=task.project_id.id
        ).create({
            'name': 'Fsm subtask',
            'partner_id': self.partner.id,
        })
        self.assertEqual(subtask.project_id, fsm_project_B)
