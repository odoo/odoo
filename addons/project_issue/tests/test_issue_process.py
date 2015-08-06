# -*- coding: utf-8 -*-

from odoo.addons.project_issue.tests.common import TestIssueUsers


class TestIssueProcess(TestIssueUsers):

    def test_issue_process(self):
        # Sending mail to get more details.

        vals = {'email_from': 'support@mycompany.com',
                'email_to': 'Robert_Adersen@yahoo.com',
                'subject': 'We need more details regarding your issue in HR module',
                'body_html': """
                    <p>
                        Hello Mr. Adersen,
                    </p>
                    <p>
                        We need more details about your issue in the HR module. Could you please
                        send us complete details about the error eg. error message, traceback
                        or what operations you were doing when you the error occured ?
                    </p>
                    <p>
                        Thank You.
                    </p>
                    <pre>
--
YourCompany
info@yourcompany.example.com
+1 555 123 8069
                    </pre>
                """}
        crm_bug_id = self.ref('project_issue.crm_case_buginaccountsmodule0')
        mail = self.env["mail.mail"].with_context(active_model='project.issue',
                                                  active_id=crm_bug_id,
                                                  active_ids=[crm_bug_id]).create(vals)
        mail.send()
