from odoo.addons.test_mail.data.test_mail_data import MAIL_EML_ATTACHMENT
from odoo.tests.common import tagged, RecordCapturer
from odoo.addons.mail.tests.common import MailCommon
from odoo.tools import mute_logger


@tagged("post_install", "-at_install", "documents_account_multicompany_mail")
class TestMultiCompanyDocumentsAccountMail(MailCommon):
    """
    Tests incoming email processing for documents_account in a multi-company setup
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "mail.catchall.domain", "alias.company2.com"
        )

        cls.mail_alias_domain_c2 = cls.env["mail.alias.domain"].create({
            "name": "alias.company2.com",
            "company_ids": [(4, cls.company_2.id)],
        })

        cls.journal_company2 = (
            cls.env["account.journal"]
            .with_company(cls.company_2)
            .create({
                "name": "Vendor Bills (Company 2)",
                "type": "purchase",
                "code": "BILLC2",
            })
        )

        cls.folder_finance_company2 = cls.env["documents.document"].create({
            "name": "Finance Company 2",
            "type": "folder",
            "company_id": cls.company_2.id,
        })

        # Enable centralization of accounting in one documents folder for company_2
        cls.company_2.documents_account_settings = True
        cls.company_2.account_folder_id = cls.folder_finance_company2.id

        # Link the journal to the folder
        cls.env["documents.account.folder.setting"].create({
            "folder_id": cls.folder_finance_company2.id,
            "journal_id": cls.journal_company2.id,
            "company_id": cls.company_2.id,
        })

    @mute_logger("odoo.addons.mail.models.mail_thread")
    def test_incoming_mail_to_journal_alias_attachment_company(self):
        """
        Tests that incoming emails with attachments are correctly processed and documents
        centralized in the correct company's folder when using multi-company setup and aliases,
        specifically in the context where the target folder belongs to a specific company.
        """
        email_from = "external.sender@example.com"

        # required because of how `format_and_process` & `account_move.create()` work
        subject = "Draft Bill"
        target_field = "display_name"

        email_to = self.journal_company2.alias_email

        with (
            self.mock_mail_gateway(),
            RecordCapturer(self.env["account.move"], []) as move_capture,
            RecordCapturer(self.env["documents.document"], []) as doc_capture,
        ):
            self.format_and_process(
                MAIL_EML_ATTACHMENT,
                email_from,
                email_to,
                subject=subject,
                target_model="account.move",
                msg_id="<account-company-2-mail-test@odoo.com>",
                target_field=target_field,
            )

        new_move = move_capture.records[0]
        self.assertEqual(
            len(new_move),
            1,
            "Should have created exactly one new account move from the email.",
        )
        self.assertEqual(
            new_move.company_id,
            self.company_2,
            "The new account move should belong to Company 2.",
        )
        new_document = doc_capture.records
        self.assertEqual(
            len(new_document),
            1,
            "Should have created exactly one new document from the email attachment.",
        )
        self.assertEqual(
            new_document.company_id,
            self.company_2,
            "The new document should be linked to Company 2.",
        )
        self.assertEqual(
            new_document.folder_id,
            self.folder_finance_company2,
            "The new document should be in Company 2's finance folder.",
        )
