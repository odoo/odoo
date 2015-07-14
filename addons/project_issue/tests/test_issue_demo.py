from openerp.addons.project_issue.tests.commons import TestIssueUsers


class TestIssueDemo(TestIssueUsers):

    def test_issue_demo(self):
        self.project_issue_model = self.env["project.issue"]

        # Test the whole create project issue with project manager.
        self.project_task_1 = self.project_issue_model.sudo(self.project_manager.id).create({
            'name': 'Error in account module',
            'task_id': self.env.ref('project.project_task_17').id})

        self.project01 = self.project_issue_model.sudo(self.project_manager.id).create({
            'name': 'OpenERP Integration',
            'project_id': self.env.ref('project.project_project_2').id})
