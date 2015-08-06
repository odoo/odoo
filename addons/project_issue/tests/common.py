# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestIssueUsers(TransactionCase):
    """Tests for unit of res users"""

    def setUp(self):
        super(TestIssueUsers, self).setUp()
        self.ProjectIssue = self.env["project.issue"]

        # Created a user as 'Project Manager'
        # Added group for Project Manager.
        self.project_manager = self.env["res.users"].create({
            'name': 'Project Manager',
            'login': 'prim',
            'password': 'prim',
            'email': 'issuemanager@yourcompany.com',
            'groups_id': [(6, 0, [self.ref('project.group_project_manager')])]
        })
