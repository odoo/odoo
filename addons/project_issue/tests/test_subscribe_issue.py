from openerp.addons.project_issue.tests.commons import TestIssueUsers
from openerp.modules import module


class TestSubscribeIssue(TestIssueUsers):

    def test_subscribe_issues(self):
        self.mail_thread_model = self.env["mail.thread"]

        # In Order to test process of  Issue in OpenERP, Customer send the issue by email.
        request_file = open(module.get_module_resource('project_issue', 'tests', 'issue.eml'), 'rb')
        request_message = request_file.read()
        self.mail_thread_model.message_process('project.issue', request_message)

        # After getting the mail, I check details of new issue of that customer.
        issue_records = self.project_issue_model.search([('email_from', '=', 'Robert Adersen <Robert_Adersen@yahoo.com>')])
        assert issue_records and len(issue_records), "issue is not created after getting request"
        issue = issue_records[0]
        assert not issue.partner_id, "Customer should be a new"
        assert issue.name == "Error in the account module", "Subject does not match"
