# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.test_mail.data.test_mail_data import MAIL_EML_ATTACHMENT
from odoo.tests.common import RecordCapturer, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install', 'documents_project')
class TestDocumentsMixinMulticompany(MailCommon):
    """
    Test documents creation via mail alias in a multi-company setup,
    specifically when targeting a project/task linked to a folder
    owned by a specific company. This mostly tests if documents.mixin
    correctly handles `company_id` while getting the default values for
    document creation.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create Project in Company 2 (and make document folders company specific)
        # This will auto-create a documents folder linked to the project
        cls.project_company_2 = cls.env['project.project'].with_user(cls.user_admin).create({
            'name': 'Project Company 2 for Mail Test',
            'company_id': cls.company_2.id,
            'alias_name': 'project-company-b-mail',
            'alias_domain_id': cls.mail_alias_domain_c2.id,
        })

        # Get the documents folder automatically created for the project
        cls.project_documents_folder_2 = cls.project_company_2.documents_folder_id

        cls.assertTrue(cls.project_documents_folder_2, "Project should have an associated documents folder.")
        cls.project_documents_folder_2.company_id = cls.company_2

        cls.email_filenames = ['attachment', 'original_msg.eml']

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_incoming_mail_to_project_alias_attachment_company(self):
        """
        Test that documents created via incoming email to a project alias
        have the correct company_id (inherited from the project's documents folder),
        and that no alias domain mismatch error occurs (if the project/task folder
        is company restricted).
        """
        subject = "New Task and Document via Email for Company 2 Project"
        email_from = 'external.sender@example.com'
        email_to = f'{self.project_company_2.alias_id.alias_name}@{self.mail_alias_domain_c2.name}'

        with (
            self.mock_mail_gateway(),
            RecordCapturer(self.env['project.task'], []) as task_capture,
            RecordCapturer(self.env['documents.document'], []) as doc_capture
        ):
            self.format_and_process(
                MAIL_EML_ATTACHMENT,
                email_from,
                email_to,
                subject=subject,
                target_model='project.project',  # Target model for mail gateway
                msg_id='<project-company-2-mail-test@odoo.com>',
            )

        # Verify a new task was created under the project
        new_task = task_capture.records
        self.assertEqual(len(new_task), 1, "Should have created exactly one new task from the email.")

        self.assertEqual(new_task.company_id.id, self.company_2.id)

        # Retrieve the newly created documents associated with the new task
        # Filter captured documents to only those linked to the new task and with expected names
        new_documents = doc_capture.records
        self.assertEqual(set(new_documents.mapped('name')), set(self.email_filenames))

        self.assertEqual(new_documents.folder_id, self.project_documents_folder_2,
                         "Documents should be in the project folder.")
        self.assertEqual(new_documents.company_id, self.company_2,
                         "Documents company should match the project's folder's company.")

        for doc in new_documents:
            self.assertIn(
                self.company_2,
                doc.alias_id.alias_domain_id.company_ids,
                f"Alias domain company for {doc.name} should include Company 2.",
            )
