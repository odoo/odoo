# -*- coding: utf-8 -*-

from odoo.addons.project_issue.tests.common import TestIssueUsers


class TestIssueProcess(TestIssueUsers):

    def test_issue_process(self):
        # Sending mail to get more details.

        vals = {'email_from': 'support@mycompany.com',
                'email_to': 'Robert_Adersen@yahoo.com',
                'subject': 'Regarding error in HR module we needs more details',
                'body_html': """
                    <p>
                        Hello Robert Adersen,
                    </p>
                    <p>
                        We just got the version and HR module as error descirption, We needs more details
                        of error to trace. Kindly send complete details of error eg. error message, traceback
                        or such operation where you found an error.
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
