from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestImportSodaFile(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='be_comp'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env.company.vat = 'BE0477472701'
        cls.misc_journal = cls.env['account.journal'].create({
            'name': 'Miscellaneous',
            'code': 'SODA',
            'type': 'general',
        })
        cls.soda_file_path = 'l10n_be_codabox/test_soda_file/soda_testing_file.xml'

    def test_soda_file_import_auto_mapping(self):
        """
        With CodaBox, if a mapping is not found for an imported Soda account, we should put it in
        the Suspense Account.
        When the user manually updates the generated entry and modifies the Suspense Account to
        an account of its choice, the global mapping should be updated too for future imports.
        :return:
        """
        with file_open(self.soda_file_path, 'rb') as soda_file:
            wizard_action = self.misc_journal.create_document_from_attachment(self.env['ir.attachment'].create({
                'mimetype': 'application/xml',
                'name': 'soda_testing_file.xml',
                'raw': soda_file.read(),
            }).ids)
            company = self.misc_journal.company_id
            self.assertEqual(wizard_action['res_model'], 'soda.import.wizard')
            wizard = self.env['soda.import.wizard'].browse(wizard_action['res_id'])
            result = wizard.action_save_and_import()
            move = self.env['account.move'].browse(result['res_id'])

            account_453 = self.env["account.chart.template"].ref('a453')
            account_455 = self.env["account.chart.template"].ref('a455')
            suspense_account = company.account_journal_suspense_account_id
            # Suspense account should be used for unmapped account 123456 (see test file)
            self.assertRecordValues(move.line_ids, [
                {'debit': 0, 'credit': 4000.00, 'name': 'Withholding Taxes', 'account_id': account_453.id},
                {'debit': 0, 'credit': 11655.1, 'name': 'Special remuneration', 'account_id': account_455.id},
                {'debit': 15655.1, 'credit': 0, 'name': 'Non-mapped account', 'account_id': suspense_account.id},
            ])

            # Global Soda mapping should be updated
            self.assertRecordValues(wizard.soda_account_mapping_ids, [
                {"code": "4530", "account_id": account_453.id},
                {"code": "4550", "account_id": account_455.id},
                {"code": "123456", "account_id": False},
            ])

            # Now we manually update the entry to replace the temporary Suspense Account to another account
            account_454 = self.env["account.chart.template"].ref('a454')
            move.line_ids[-1].account_id = account_454
            self.assertRecordValues(move.line_ids, [
                {'debit': 0, 'credit': 4000.00, 'name': 'Withholding Taxes', 'account_id': account_453.id},
                {'debit': 0, 'credit': 11655.1, 'name': 'Special remuneration', 'account_id': account_455.id},
                {'debit': 15655.1, 'credit': 0, 'name': 'Non-mapped account', 'account_id': account_454.id},
            ])

            # Global Soda mapping should now be updated too
            self.assertRecordValues(wizard.soda_account_mapping_ids, [
                {"code": "4530", "account_id": account_453.id},
                {"code": "4550", "account_id": account_455.id},
                {"code": "123456", "account_id": account_454.id},
            ])

            # However, updating the mapping shouldn't affect already created entries
            wizard.soda_account_mapping_ids[-1].account_id = account_453
            self.assertEqual(move.line_ids[-1].account_id, account_454)
