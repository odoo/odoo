# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import UserError


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestImportZenginBankStatement(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('jp')
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_journal = cls.company_data['default_journal_bank']

    def test_zengin_transfer_file_import(self):
        with self.assertRaisesRegex(UserError, "The following files could not be imported"):
            zengin_transfer_utf8_file = (
                b'10100504050503240503310009\xef\xbe\x90\xef\xbe\x82\xef\xbd\xb2\xef\xbd\xbd\xef\xbe\x90\xef\xbe\x84\xef\xbe\x93        410\xef\xbd\xbb\xef\xbe\x9d\xef\xbe\x89\xef\xbe\x90\xef\xbe\x94          10355368\xef\xbe\x9c\xef\xbd\xb6\xef\xbd\xb8\xef\xbd\xbb\xef\xbd\xbc\xef\xbe\x96\xef\xbd\xb3\xef\xbd\xb6\xef\xbd\xb2                                                                                                                           \r\n'
                b'203000105032405032400000600000000000000          \xef\xbe\x9c\xef\xbd\xb6\xef\xbd\xb8\xef\xbd\xbb \xef\xbd\xb2\xef\xbe\x81\xef\xbe\x9b\xef\xbd\xb3                                       \xef\xbe\x90\xef\xbe\x82\xef\xbd\xb2\xef\xbd\xbd\xef\xbe\x90\xef\xbe\x84\xef\xbe\x93        \xef\xbd\xbb\xef\xbe\x9d\xef\xbe\x89\xef\xbe\x90\xef\xbe\x94                                                                                  \r\n'
                b'203000205032905032900000000000000000000          \xef\xbe\x9c\xef\xbd\xb6\xef\xbd\xb8\xef\xbd\xbb\xef\xbd\xbc\xef\xbe\x96\xef\xbd\xb3\xef\xbd\xbc\xef\xbe\x9e(\xef\xbd\xb6                                     \xef\xbe\x90\xef\xbe\x82\xef\xbd\xb2\xef\xbd\xbd\xef\xbe\x90\xef\xbe\x84\xef\xbe\x93        \xef\xbd\xbb\xef\xbe\x9d\xef\xbe\x89\xef\xbe\x90\xef\xbe\x94           050000000000000000000000                                               \r\n'
                b'8000002050000060000000000000000000000                                                                                                                                                                  \r\n9                                                                                                                                                                                                      \r\n')
            self.company_data['default_journal_bank'].create_document_from_attachment(self.env['ir.attachment'].create({
                'mimetype': 'application/text',
                'name': 'zengin_transfer_utf8.txt',
                'raw': zengin_transfer_utf8_file,
            }).ids)

        zengin_transfer_file = (
            b'10100504050503240503310009\xd0\xc2-\xb2\xbd\xd0\xc4\xd3       410\xbb\xdd\xc9\xd0\xd4          10355368\xdc\xb6\xb8\xbb\xbc\xd6\xb3\xb6\xb2                                                                                                                           \r\n'
            b'203000105032405032400000600000000000000          \xdc\xb6\xb8\xbb \xb2\xc1\xdb\xb3                                       \xd0\xc2\xb2\xbd\xd0\xc4\xd3        \xbb\xdd\xc9\xd0\xd4                                                                                  \r\n'
            b'203000205032905032900000000000000000000          \xdc\xb6\xb8\xbb\xbc\xd6\xb3\xbc\xde(\xb6                                     \xd0\xc2\xb2\xbd\xd0\xc4\xd3        \xbb\xdd\xc9\xd0\xd4           050000000000000000000000                                               \r\n'
            b'8000002050000060000000000000000000000                                                                                                                                                                  \r\n'
            b'9                                                                                                                                                                                                      \r\n')
        self.company_data['default_journal_bank'].create_document_from_attachment(self.env['ir.attachment'].create({
            'mimetype': 'application/text',
            'name': 'zengin_transfer.txt',
            'raw': zengin_transfer_file,
        }).ids)
        imported_statement = self.env['account.bank.statement'].search([('company_id', '=', self.env.company.id)])
        self.assertRecordValues(imported_statement, [{
            'balance_start': 0.0,
            'balance_end_real': 50000060000.0,
        }])

    def test_zengin_deposit_withdrawal_file_import(self):
        zengin_deposit_withdrawal_file = (
            b'10300504050503130503310009\xd0\xc2\xb2\xbd\xd0\xc4\xd3        410\xbb\xdd\xc9\xd0\xd4          00010000355368\xdc\xb6\xb8\xbb\xbc\xd6\xb3\xb6\xb2                               1100099028913211                                                                       \r\n'
            b'203000001050313050313111000000060000000000000000                                 \xdc\xb6\xb8\xbb \xb2\xc1\xdb\xb3                                       \xd0\xc2\xb2\xbd\xd0\xc4\xd3        \xbb\xdd\xc9\xd0\xd4          \xcc\xd8\xba\xd0                                     \r\n'
            b'203000002050331050331214000000005000000000000000                                                                                                               \xbf\xc9\xc0\xd6\xb7\xdd              0                    \r\n'
            b'8000001000000006000000000100000000050001000990289132110000002                                                                                                                                           \r\n'
            b'9000000001300001                                                                                                                                                                                       \r\n')
        self.company_data['default_journal_bank'].create_document_from_attachment(self.env['ir.attachment'].create({
            'mimetype': 'application/text',
            'name': 'zengin_deposit_withdrawal.txt',
            'raw': zengin_deposit_withdrawal_file,
        }).ids)
        imported_statement = self.env['account.bank.statement'].search([('company_id', '=', self.env.company.id)])
        self.assertRecordValues(imported_statement, [{
            'balance_start': 99028913211.0,
            'balance_end_real': 99028968211.0,
        }])
