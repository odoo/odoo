# -*- coding: utf-8 -*-

from odoo.addons.project_issue.tests.common import TestIssueUsers
from odoo.modules import module


class TestSubscribeIssue(TestIssueUsers):

    def test_subscribe_issues(self):
        # In Order to test process of Issue in Odoo, Customer send the issue by email.
        request_file = open(module.get_module_resource('project_issue', 'tests', 'issue.eml'), 'rb')
        request_message = request_file.read()
        self.env["mail.thread"].message_process('project.issue', request_message)

        # After getting the mail, Check details of new issue of that customer.
        issue = self.ProjectIssue.search([('email_from', '=', 'Robert Adersen <Robert_Adersen@yahoo.com>')], limit=1)
        self.assertEquals(len(issue), 1, "Issue is not created after getting request")
        self.assertFalse(issue.partner_id, "Customer should be a new")
        self.assertEquals(issue.name, "Error in the account module", "Subject does not match")
