from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import tagged

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestFECExport(AccountTestInvoicingCommon):
    def test_fec_export(self):
        self.init_invoice("out_invoice", self.partner_a, "2019-01-01", amounts=[1000, 2000], post=True)
        self.init_invoice("out_invoice", self.partner_a, "2020-01-01", amounts=[1000, 2000], post=True)
        # Create a new FEC export
        fec_export = self.env['l10n_fr.fec.export.wizard'].create({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })
        result = fec_export.generate_fec()
        self.assertEqual(
            result['file_content'].decode(),
            'JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib|CompAuxNum|CompAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit|EcritureLet|DateLet|ValidDate|Montantdevise|Idevise\r\n'
            'OUV|Balance initiale|OUVERTURE/2020|20200101|999999|Undistributed Profits/Losses|||-|20200101|/|0,00| 000000000003000,00|||20200101||\r\n'
            f'OUV|Balance initiale|OUVERTURE/2020|20200101|121000|Account Receivable|{self.partner_a.id}|partner_a|-|20200101|/| 000000000003000,00|0,00|||20200101||\r\n'
            'INV|Customer Invoices|INV/2020/00001|20200101|400000|Product Sales|||-|20200101|test line|0,00| 000000000001000,00|||20200101|-000000000001000,00|USD\r\n'
            'INV|Customer Invoices|INV/2020/00001|20200101|400000|Product Sales|||-|20200101|test line|0,00| 000000000002000,00|||20200101|-000000000002000,00|USD\r\n'
            f'INV|Customer Invoices|INV/2020/00001|20200101|121000|Account Receivable|{self.partner_a.id}|partner_a|-|20200101|INV/2020/00001| 000000000003000,00|0,00|||20200101| 000000000003000,00|USD'
        )
