from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import tagged

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestFECExport(AccountTestInvoicingCommon):
    def test_fec_export(self):
        self.init_invoice("out_invoice", self.partner_a, "2019-01-01", amounts=[1000, 2000], post=True)
        inv = self.init_invoice("out_invoice", self.partner_a, "2020-01-01", amounts=[1000, 2000])
        inv.write({
            "line_ids": [
                Command.create({
                    "name": "Note",
                    "display_type": "line_note",
                })
            ]
        })
        inv.action_post()
        # Clear the label of the receivable line to test the fallback logic (partner_name - move_ref)
        inv.line_ids.filtered(lambda l: l.display_type == 'payment_term').name = ''
        # Create a new FEC export
        fec_export = self.env['l10n_fr.fec.export.wizard'].create({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })
        result = fec_export.with_context(fec_test_mode=True).generate_fec()
        self.assertEqual(
            b''.join(result['file_content']).decode(),
            'JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib|CompAuxNum|CompAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit|EcritureLet|DateLet|ValidDate|Montantdevise|Idevise\r\n'
            'OUV|Balance initiale|OUVERTURE/2020|20200101|999999|Profit or Loss Appropriation|||-|20200101|Balance initiale|0,00| 000000000003000,00|||20200101||\r\n'
            f'OUV|Balance initiale|OUVERTURE/2020|20200101|121000|Account Receivable|{self.partner_a.id}|partner_a|-|20200101|Balance initiale| 000000000003000,00|0,00|||20200101||\r\n'
            'INV|Sales|INV/2020/00001|20200101|400000|Product Sales|||-|20200101|test line|0,00| 000000000001000,00|||20200101|-000000000001000,00|USD\r\n'
            'INV|Sales|INV/2020/00001|20200101|400000|Product Sales|||-|20200101|test line|0,00| 000000000002000,00|||20200101|-000000000002000,00|USD\r\n'
            f'INV|Sales|INV/2020/00001|20200101|121000|Account Receivable|{self.partner_a.id}|partner_a|-|20200101|partner_a - INV/2020/00001| 000000000003000,00|0,00|||20200101| 000000000003000,00|USD'
        )

    def test_fec_sub_companies(self):
        """When exporting FEC, data from child companies should be included"""
        main_company = self.env.company
        branch_a, branch_b = self.env['res.company'].create([
            {
                'name': 'Branch A',
                'country_id': main_company.country_id.id,
                'parent_id': main_company.id,
            }, {
                'name': 'Branch B',
                'country_id': main_company.country_id.id,
                'parent_id': main_company.id
            }
        ])
        branch_a1 = self.env['res.company'].create({
            'name': 'Branch A1',
            'country_id': main_company.country_id.id,
            'parent_id': branch_a.id,
        })

        self.cr.precommit.run()  # load the COA
        all_companies = (main_company + branch_a + branch_a1 + branch_b)

        for i, company in enumerate(all_companies, start=1):
            self.init_invoice('out_invoice', invoice_date="2021-01-01", post=True, amounts=[i * 100], company=company)

        fec_export = self.env['l10n_fr.fec.export.wizard'].create({
            'date_from': '2021-01-01',
            'date_to': '2021-12-31',
        })
        result = fec_export.with_context(fec_test_mode=True).generate_fec()
        self.assertEqual(
            b''.join(result['file_content']).decode(),
            "JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib|CompAuxNum|CompAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit|EcritureLet|DateLet|ValidDate|Montantdevise|Idevise\r\n"
            "INV|Sales|INV/2021/00001|20210101|400000|Product Sales|||-|20210101|test line|0,00| 000000000000100,00|||20210101|-000000000000100,00|USD\r\n"
            f"INV|Sales|INV/2021/00001|20210101|121000|Account Receivable|{self.partner_a.id}|partner_a|-|20210101|INV/2021/00001| 000000000000100,00|0,00|||20210101| 000000000000100,00|USD\r\n"
            "INV|Sales|INV/2021/00002|20210101|400000|Product Sales|||-|20210101|test line|0,00| 000000000000200,00|||20210101|-000000000000200,00|USD\r\n"
            f"INV|Sales|INV/2021/00002|20210101|121000|Account Receivable|{self.partner_a.id}|partner_a|-|20210101|INV/2021/00002| 000000000000200,00|0,00|||20210101| 000000000000200,00|USD\r\n"
            "INV|Sales|INV/2021/00003|20210101|400000|Product Sales|||-|20210101|test line|0,00| 000000000000300,00|||20210101|-000000000000300,00|USD\r\n"
            f"INV|Sales|INV/2021/00003|20210101|121000|Account Receivable|{self.partner_a.id}|partner_a|-|20210101|INV/2021/00003| 000000000000300,00|0,00|||20210101| 000000000000300,00|USD\r\n"
            "INV|Sales|INV/2021/00004|20210101|400000|Product Sales|||-|20210101|test line|0,00| 000000000000400,00|||20210101|-000000000000400,00|USD\r\n"
            f"INV|Sales|INV/2021/00004|20210101|121000|Account Receivable|{self.partner_a.id}|partner_a|-|20210101|INV/2021/00004| 000000000000400,00|0,00|||20210101| 000000000000400,00|USD"
        )

        # Select only parent company
        self.env.user.write({
            'company_ids': [Command.set(main_company.ids)],
            'company_id': main_company.id,
        })

        fec_export = self.env['l10n_fr.fec.export.wizard'].create({
            'date_from': '2021-01-01',
            'date_to': '2021-12-31',
        })
        result = fec_export.with_context(fec_test_mode=True).generate_fec()
        self.assertEqual(
            b''.join(result['file_content']).decode(),
            "JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib|CompAuxNum|CompAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit|EcritureLet|DateLet|ValidDate|Montantdevise|Idevise\r\n"
            "INV|Sales|INV/2021/00001|20210101|400000|Product Sales|||-|20210101|test line|0,00| 000000000000100,00|||20210101|-000000000000100,00|USD\r\n"
            f"INV|Sales|INV/2021/00001|20210101|121000|Account Receivable|{self.partner_a.id}|partner_a|-|20210101|INV/2021/00001| 000000000000100,00|0,00|||20210101| 000000000000100,00|USD"
        )

    def test_fec_initial_balance_skips_zero_net_openings(self):
        """An account whose prior-year movements net to zero must not produce
        an empty 'Balance initiale' (OUVERTURE) line in the next fiscal year.
        """
        account = self.copy_account(self.company_data['default_account_assets'])
        revenue = self.company_data['default_account_revenue']
        misc_journal = self.company_data['default_journal_misc']

        self.env['account.move'].create([
            {
                'move_type': 'entry',
                'date': '2019-06-01',
                'journal_id': misc_journal.id,
                'line_ids': [
                    Command.create({'account_id': account.id, 'debit': 100.0}),
                    Command.create({'account_id': account.id, 'credit': 100.0}),
                ],
            },
            {
                'move_type': 'entry',
                'date': '2020-06-01',
                'journal_id': misc_journal.id,
                'line_ids': [
                    Command.create({'account_id': account.id, 'debit': 50.0}),
                    Command.create({'account_id': revenue.id, 'credit': 50.0}),
                ],
            },
        ]).action_post()

        fec_export = self.env['l10n_fr.fec.export.wizard'].create({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })
        result = fec_export.with_context(fec_test_mode=True).generate_fec()
        self.assertEqual(
            b''.join(result['file_content']).decode(),
            'JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib|CompAuxNum|CompAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit|EcritureLet|DateLet|ValidDate|Montantdevise|Idevise\r\n'
            f'MISC|Miscellaneous Operations|MISC/2020/06/0001|20200601|{account.code}|{account.name}|||-|20200601|MISC/2020/06/0001| 000000000000050,00|0,00|||20200601| 000000000000050,00|USD\r\n'
            'MISC|Miscellaneous Operations|MISC/2020/06/0001|20200601|400000|Product Sales|||-|20200601|MISC/2020/06/0001|0,00| 000000000000050,00|||20200601|-000000000000050,00|USD'
        )

    def test_fec_initial_balance_skips_zero_net_partner_openings(self):
        """A partner whose prior-year receivable nets to zero must not produce
        an empty per-partner 'Balance initiale' (OUVERTURE) line.
        """
        receivable = self.company_data['default_account_receivable']
        revenue = self.company_data['default_account_revenue']
        misc_journal = self.company_data['default_journal_misc']

        self.env['account.move'].create([
            {
                'move_type': 'entry',
                'date': '2019-06-01',
                'journal_id': misc_journal.id,
                'line_ids': [
                    Command.create({'account_id': receivable.id, 'partner_id': self.partner_a.id, 'debit': 100.0}),
                    Command.create({'account_id': receivable.id, 'partner_id': self.partner_a.id, 'credit': 100.0}),
                ],
            },
            {
                'move_type': 'entry',
                'date': '2020-06-01',
                'journal_id': misc_journal.id,
                'line_ids': [
                    Command.create({'account_id': receivable.id, 'partner_id': self.partner_a.id, 'debit': 50.0}),
                    Command.create({'account_id': revenue.id, 'credit': 50.0}),
                ],
            },
        ]).action_post()

        fec_export = self.env['l10n_fr.fec.export.wizard'].create({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })
        result = fec_export.with_context(fec_test_mode=True).generate_fec()
        self.assertEqual(
            b''.join(result['file_content']).decode(),
            'JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib|CompAuxNum|CompAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit|EcritureLet|DateLet|ValidDate|Montantdevise|Idevise\r\n'
            f'MISC|Miscellaneous Operations|MISC/2020/06/0001|20200601|121000|Account Receivable|{self.partner_a.id}|partner_a|-|20200601|partner_a - MISC/2020/06/0001| 000000000000050,00|0,00|||20200601| 000000000000050,00|USD\r\n'
            'MISC|Miscellaneous Operations|MISC/2020/06/0001|20200601|400000|Product Sales|||-|20200601|MISC/2020/06/0001|0,00| 000000000000050,00|||20200601|-000000000000050,00|USD'
        )


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestFECExportFR(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('fr')
    def setUpClass(self):
        super().setUpClass()

    def test_fec_foreign_currency_mismatch_amount_currency_and_currency_id(self):
        """According to the law of France, the absence of an amount should lead to an absence
        of the currency. Both columns in the FEC must be either empty of filled.
        https://bofip.impots.gouv.fr/bofip/9028-PGP.html/identifiant%3DBOI-CF-IOR-60-40-20-20170607#III._Donnees_devant_figurer_12
        """
        # 0. Set up dates
        dates = {
            "january-start": '2026-01-01',
            "invoice-date": '2026-01-10',
            "statement-date": '2026-01-15',
            "january-end": '2026-01-31',
        }
        # 1. Set up exchange rates
        usd = self.setup_other_currency('USD', rates=[
            (dates["invoice-date"], 1),
            (dates["statement-date"], 0.5),
        ])
        # 2. Create an invoice in USD (INV)
        invoice = self._create_invoice(
            invoice_date=dates["invoice-date"],
            currency_id=usd,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=100, tax_ids=self.env['account.tax']),
            ],
            post=True,
        )
        invoice_receivable_line = invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term')
        # 3. Create a bank statement line (BNK)
        statement_line = self.env['account.bank.statement.line'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'amount': 200,
            'foreign_currency_id': usd.id,
            'amount_currency': 100.0,
            'date': dates["statement-date"],
            'payment_ref': invoice.name,
            'partner_id': self.partner_a.id,
        })
        # 4. Reconcile (EXCH)
        _, statement_suspense_line, _ = statement_line._seek_for_lines()
        statement_suspense_line.account_id = invoice_receivable_line.account_id
        (statement_suspense_line + invoice_receivable_line).reconcile()
        self.assertTrue(statement_line.is_reconciled)
        self.assertEqual(invoice.payment_state, 'paid')
        full_reconcile_id = invoice_receivable_line.full_reconcile_id.id
        # 5. Export the FEC
        fec_export = self.env['l10n_fr.fec.export.wizard'].create({
            'date_from': dates["january-start"],
            'date_to': dates["january-end"],
        })
        result = fec_export.with_context(fec_test_mode=True).generate_fec()
        self.assertEqual(
            b''.join(result['file_content']).decode(),
            'JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib|CompAuxNum|CompAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit|EcritureLet|DateLet|ValidDate|Montantdevise|Idevise\r\n'
            'INV|Sales|INV/2026/00001|20260110|707000|Sales of goods|||-|20260110|INV/2026/00001|0,00| 000000000000100,00|||20260110|-000000000000100,00|USD\r\n'
            f'INV|Sales|INV/2026/00001|20260110|411100|Customers - Sales of goods or services|{self.partner_a.id}|partner_a|-|20260110|INV/2026/00001| 000000000000100,00|0,00|{full_reconcile_id}|20261116|20260110| 000000000000100,00|USD\r\n'
            'BNK1|Bank|BNK1/2026/00001|20260115|512001|Bank|||-|20260115|INV/2026/00001| 000000000000200,00|0,00|||20260115| 000000000000200,00|EUR\r\n'
            f'BNK1|Bank|BNK1/2026/00001|20260115|411100|Customers - Sales of goods or services|{self.partner_a.id}|partner_a|-|20260115|INV/2026/00001|0,00| 000000000000200,00|{full_reconcile_id}|20261116|20260115|-000000000000100,00|USD\r\n'
            f'EXCH|Exchange Difference|EXCH/2026/01/0001|20260131|411100|Customers - Sales of goods or services|{self.partner_a.id}|partner_a|-|20260131|Currency exchange rate difference| 000000000000100,00|0,00|{full_reconcile_id}|20261116|20260131||\r\n'
            'EXCH|Exchange Difference|EXCH/2026/01/0001|20260131|766000|Exchange gains|||-|20260131|Currency exchange rate difference|0,00| 000000000000100,00|||20260131||',
        )
