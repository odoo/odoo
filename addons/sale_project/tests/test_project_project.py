# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged('-at_install', 'post_install')
class TestProjectProject(TransactionCase):
    def test_projects_to_make_billable(self):
        """ Test the projects fetched in the post init are the ones expected """
        Project = self.env['project.project']
        Task = self.env['project.task']
        partner = self.env['res.partner'].create({'name': "Mur en béton"})
        project1, project2, project3 = Project.create([
            {'name': 'Project with partner', 'partner_id': partner.id, 'allow_billable': False},
            {'name': 'Project without partner', 'allow_billable': False},
            {'name': 'Project without partner 2', 'allow_billable': False},
        ])
        Task.create([
            {'name': 'Task with partner in project 2', 'project_id': project2.id, 'partner_id': partner.id},
            {'name': 'Task without partner in project 2', 'project_id': project2.id},
            {'name': 'Task without partner in project 3', 'project_id': project3.id},
        ])
        projects_to_make_billable = Project.search(Project._get_projects_to_make_billable_domain())
        non_billable_projects, = Task._read_group(
            Task._get_projects_to_make_billable_domain([('project_id', 'not in', projects_to_make_billable.ids)]),
            [],
            ['project_id:recordset'],
        )[0]
        projects_to_make_billable += non_billable_projects
        self.assertEqual(projects_to_make_billable, project1 + project2)

    def test_onchange_allow_billable_warning(self):
        project = self.env['project.project'].create({
            'name': 'Test Project',
            'allow_billable': True,
        })
        expected_msg = self.env._(
            "If you mark this project as non-billable, all tasks will be disconnected from customers and "
            "sales orders. You won't be able to recover this data if you decide to make the project billable "
            "again later. Are you sure you want to do this?"
        )

        with self.assertLogs('odoo.tests.form.onchange', 'WARNING') as captured_logs:
            with Form(project) as form:
                form.allow_billable = False
        self.assertTrue(
            captured_logs.output[0].startswith('WARNING:odoo.tests.form.onchange:'),
            "A warning should be logged when marking an existing project as non-billable.",
        )
        self.assertIn(
            expected_msg,
            captured_logs.output[0],
            "Warning message should match expected when disabling billable.",
        )

        # No warning should be logged when creating a non-billable project
        with self.assertNoLogs('odoo.tests.form.onchange', 'WARNING'):
            with Form(self.env['project.project']) as project_form:
                project_form.name = 'New Project'
                project_form.allow_billable = False
