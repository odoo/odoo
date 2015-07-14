from openerp.tests.common import TransactionCase


class TestIssueUsers(TransactionCase):
    """Tests for unit of res users"""

    def setUp(self):
        super(TestIssueUsers, self).setUp()
        ResUsers = self.env["res.users"]
        self.ProjectIssue = self.env["project.issue"]

        # Create a user as 'Project manager'
        # I added groups for Project manager.
        self.project_manager = ResUsers.create({
            'name': 'Project Manager',
            'login': 'prim',
            'password': 'prim',
            'email': 'issuemanager@yourcompany.com',
            'groups_id': [(6, 0, [self.env.ref('project.group_project_manager').id])]})
