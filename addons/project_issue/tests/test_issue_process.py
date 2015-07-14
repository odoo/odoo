from openerp.addons.project_issue.tests.commons import TestIssueUsers


class TestSubscribeIssue(TestIssueUsers):

    def test_issue_process(self):
        # I send mail to get more details. TODO revert mail.mail to mail.compose.message (conversion to customer should be automatic).
        MailMail = self.env["mail.mail"]
        self.crm_case_buginaccountsmodule0_id = self.env.ref('project_issue.crm_case_buginaccountsmodule0').id

        # I send mail to get more details. TODO revert mail.mail to mail.compose.message (conversion to customer should be automatic).
        ctx = dict(self.env.context)
        ctx.update({'active_model': 'project.issue', 'active_id': self.crm_case_buginaccountsmodule0_id,
                   'active_ids': [self.crm_case_buginaccountsmodule0_id]})
        MailMail.with_context(ctx).create({'email_from': 'support@mycompany.com',
                                          'email_to': 'Robert_Adersen@yahoo.com',
                                           'subject': 'Regarding error in account module we nees more details'})
        MailMail.send()
