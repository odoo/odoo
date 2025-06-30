from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged, new_test_user
from odoo.tools import file_open


@tagged('post_install', '-at_install', 'mail_alias')
class TestAccountJournalAliasOtherCompany(AccountTestInvoicingCommon, MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_2 = cls._create_company(name='company_2')
        cls.user_company_2 = new_test_user(
            cls.env,
            name="user company 2",
            login='login_user_company_2',
            password='login_user_company_2',
            email='login_user_company_2@test.com',
            company_id=cls.company_2.id,
        )

    def test_send_email_to_alias(self):
        with file_open('account/tests/test_account_journal_alias_other_company.eml', 'rb') as file:
            account_move_email = file.read()
            self.env['mail.thread'].message_process('account.move', account_move_email)
            assert self.env['account.move'].search([('invoice_source_email', '=', 'login_user_company_2@test.com')])
