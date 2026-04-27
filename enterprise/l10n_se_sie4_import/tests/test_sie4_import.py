import base64

from odoo import fields, Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import file_open
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('-at_install', 'post_install_l10n', 'post_install')
class AccountTestSIE4Import(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.chart_template = 'se'
        cls.currency = cls.env.ref('base.SEK')
        cls.company_id = cls.setup_other_company(name='SIE 4 Test Company')['company']
        cls.wizard = cls.env['l10n_se_sie4_import.wizard'].create({
            'company_id': cls.company_id.id,
            'attachment_file': base64.b64encode(b''),  # empty required attachment; to be replaced in the tests
            'import_opening_balance': True,
            'update_account_data': True,
        })
        journal_misc = cls.env['account.journal'].search(
            domain=[
                *cls.env['account.journal']._check_company_domain(cls.company_id),
                ('type', '=', 'general'),
            ],
            limit=1,
        )
        cls.journal_misc_id = journal_misc.id

        # unlink the default draft move to make searching on test easier
        cls.env['account.move'].search([('company_id', '=', cls.company_id.id)]).unlink()

    def create_sie4_data_map(self):
        return {
            'opening_balance_map': {},
            'existing_accounts_map': {},
            'journal_misc_id': self.journal_misc_id,
            'dates': {},
            'account.account': {},
            'res.company': {self.company_id.id: {}},
            'account.fiscal.year': {},
            'account.move': {},
        }

    # --------------------------------------------------------------------------
    # Import from a Real Test File
    # --------------------------------------------------------------------------

    def test_sie4_import_file(self):
        file_content = file_open('l10n_se_sie4_import/tests/test_files/sie4_import.se').read()
        self.wizard.write({
            'attachment_file': base64.b64encode(file_content.encode()),
            'company_id': self.company_id.id,
            'update_account_data': False,
            'import_opening_balance': False,
        })
        self.wizard.action_import_sie4()

        # Ensure all 18 moves from `sie4_import.se` are imported correctly
        test_date_format = '%y%m%d'
        imported_moves = self.env['account.move'].search([('company_id', '=', self.company_id.id)])
        imported_move_dates = tuple(date.strftime(test_date_format) for date in imported_moves.mapped('date'))
        self.assertEqual(len(imported_moves), 18)
        self.assertTupleEqual(imported_move_dates, (
            '240409', '240408', '240407', '240406', '240405', '240404', '240403', '240402', '240401',
            '240113', '240112', '240111', '240110', '240109', '240108', '240107', '240106', '240105',
        ))

    # --------------------------------------------------------------------------
    # Import Simple Data Tests
    # --------------------------------------------------------------------------

    def test_sie4_import_identification(self):
        self.wizard.attachment_file = base64.b64encode(b"""
            #SIETYP 4
            #FNAMN "Swedish Series"
            #ORGNR 555555-5555
            #ADRESS "Siw Eriksson" "Box 1" "123 45 STORSTAD" "012-34 56 78"
            #RAR 0 20210101 20211231
            #RAR -1 20200101 20201231
            #TAXAR 2022
            #VALUTA SEK
            #KPTYP EUBAS97
        """)
        self.wizard.action_import_sie4()

        self.assertRecordValues(self.company_id, [{
            'name': 'Swedish Series',
            'vat': 'SE555555555501',
            'street': '123 45 STORSTAD',
            'street2': 'Box 1',
            'phone': '012-34 56 78',
        }])

    def test_sie4_import_identification_without_previous_year(self):
        self.wizard.write({
            'import_opening_balance': True,
        })
        self.wizard.attachment_file = base64.b64encode(b"""
            #SIETYP 4
            #FNAMN "Swedish Series"
            #ORGNR 555555-5555
            #ADRESS "Siw Eriksson" "Box 1" "123 45 STORSTAD" "012-34 56 78"
            #RAR 0 20240101 20241231
            #TAXAR 2022
            #VALUTA SEK
            #KPTYP EUBAS97
            #VER A 1 20240107 "1st item"
            {
                #TRANS 1060 {} 300.0
                #TRANS 2030 {} -300.0
            }
            #IB 0 1030 200.0
        """)
        self.wizard.action_import_sie4()
        imported_moves = self.env['account.move'].search([('company_id', '=', self.company_id.id)])
        self.assertRecordValues(
            imported_moves,
            [
                {
                    "name": "MISC/2024/01/0001",
                    "ref": "Imported from SIE4 - 1st item",
                    "date": fields.Date.from_string("2024-01-07"),
                    "move_type": "entry",
                    "state": "draft",
                    "journal_id": self.journal_misc_id,
                },
                {
                    'name': 'MISC/2023/12/0001',
                    'ref': 'SIE opening balance move 2023-12-31',
                    'date': fields.Date.from_string("2023-12-31"),
                    'journal_id': self.journal_misc_id,
                    'move_type': 'entry',
                    'state': 'draft'
                }
            ],
        )

    def test_sie4_import_identification_with_missing_element_in_adress(self):
        self.wizard.attachment_file = base64.b64encode(b"""
            #SIETYP 4
            #FNAMN "Swedish Series"
            #ORGNR 555555-5555
            #ADRESS "Siw Eriksson" "123 45 STORSTAD" "012-34 56 78"
            #RAR 0 20210101 20211231
            #RAR -1 20200101 20201231
            #TAXAR 2022
            #VALUTA SEK
            #KPTYP EUBAS97
        """)
        with self.assertRaises(UserError) as err:
            self.wizard.action_import_sie4()

        self.assertEqual(
            (
                'Missing element in #ADRESS line.\n'
                'Expected format: "contact" "distribution address" "postal address" "telephone".\n'
                'Received data: Siw Eriksson 123 45 STORSTAD 012-34 56 78.'
            ),
            err.exception.args[0],
        )

    def test_sie4_import_chart_of_account(self):
        self.wizard.attachment_file = base64.b64encode(b"""
            #KONTO 1060 Hyresrtt
            #KTYP 1060 I
            #KONTO 1070 Goodwill
            #KTYP 1070 T
            #KONTO 2086 Reservfond
            #KTYP 2086 I
            #KONTO 2123 "Periodiseringsfond 2023"
            #KTYP 2123 I
            #KONTO 3030 "Positiv VM 25%"
            #KTYP 3030 S
            #KONTO 7836 "Avskrivningar leasade tillg"
            #KTYP 7836 K
        """)
        self.wizard.action_import_sie4()

        codes = ('1060', '1070', '2086', '2123', '3030', '7836')
        accounts = self.env['account.account'].with_company(self.company_id).search([('code', 'in', codes)])

        self.assertRecordValues(accounts, [
            {'code': '1060', 'account_type': 'income', 'name': 'Hyresrtt'},
            {'code': '1070', 'account_type': 'asset_receivable', 'name': 'Goodwill'},
            {'code': '2086', 'account_type': 'income', 'name': 'Reservfond'},
            {'code': '2123', 'account_type': 'income', 'name': 'Periodiseringsfond 2023'},
            {'code': '3030', 'account_type': 'liability_current', 'name': 'Positiv VM 25%'},
            {'code': '7836', 'account_type': 'expense', 'name': 'Avskrivningar leasade tillg'},
        ])

    def test_sie4_import_opening_balance(self):
        self.wizard.attachment_file = base64.b64encode(b"""
            #RAR -1 20200101 20201231
            #RAR  0 20210101 20211231
            #IB   0 1030 200.0
            #IB   0 1060 600.0
            #IB   0 1110 1000.0
            #IB   0 2019 -200.0
            #IB   0 2030 -600.0
            #IB   0 2060 -1000.0
        """)
        self.wizard.action_import_sie4()

        opening_move = self.env['account.move'].search([('company_id', '=', self.company_id.id)])
        self.assertRecordValues(opening_move, [{
            'name': 'MISC/2020/12/0001',
            'date': fields.Date.from_string('2020-12-31'),
            'move_type': 'entry',
            'state': 'draft',
            'journal_id': self.journal_misc_id,
            'ref': 'SIE opening balance move 2020-12-31',
        }])
        self.assertSequenceEqual(opening_move.line_ids.mapped('balance'), (200.0, 600.0, 1000.0, -200.0, -600.0, -1000.0))
        self.assertSequenceEqual(
            opening_move.line_ids.account_id.with_company(self.company_id).mapped('code'),
            ('1030', '1060', '1110', '2019', '2030', '2060'),
        )

    def test_sie4_import_opening_balance_with_existing_amount(self):
        """
        This test makes sure that when importing an opening balance item to an account that already have an existing amount,
        it will only import the remaining amounts needed to make the opening balance in the item valid.

        For example:
        - account 1030 currently have a balance of 50
        - the imported file specifies that it should have an opening balance of 200
        - the opening balance move created from the import will have a line for account 1030 with balance 150 (calculated from 200 subtracted by 50)
        """
        currency_id = self.currency.id
        codes = ('1030', '1060', '1110', '2019', '2030', '2060')
        balances = (50.0, 60.0, 70.0, -50.0, -60.0, -70.0)
        accounts = self.env['account.account'].with_company(self.company_id).search([('code', 'in', codes)])
        account_balance_map = {account.id: balance for account, balance in zip(accounts, balances)}

        # Add some balance value to offset the opening balance to each account
        offset_move = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'move_type': 'entry',
            'date': '2020-12-01',
            'invoice_date': '2020-12-01',
            'journal_id': self.journal_misc_id,
            'line_ids': [
                Command.create({'balance': balance, 'account_id': account_id, 'currency_id': currency_id})
                for account_id, balance in account_balance_map.items()
            ],
        })

        self.wizard.attachment_file = base64.b64encode(b"""
            #RAR -1 20200101 20201231
            #RAR  0 20210101 20211231
            #IB   0 1030 200.0
            #IB   0 1060 600.0
            #IB   0 1110 1000.0
            #IB   0 2019 -200.0
            #IB   0 2030 -600.0
            #IB   0 2060 -1000.0
        """)
        self.wizard.action_import_sie4()

        opening_move = self.env['account.move'].search([('company_id', '=', self.company_id.id), ('id', '!=', offset_move.id)])
        self.assertSequenceEqual(opening_move.line_ids.mapped('balance'), (150.0, 540.0, 930.0, -150.0, -540.0, -930.0))
        self.assertSequenceEqual(
            opening_move.line_ids.account_id.with_company(self.company_id).mapped('code'),
            ('1030', '1060', '1110', '2019', '2030', '2060'),
        )

    def test_sie4_import_opening_balance_with_unbalanced_ib(self):
        self.wizard.attachment_file = base64.b64encode(b"""
            #RAR -1 20200101 20201231
            #RAR  0 20210101 20211231
            #IB   0 1030 200.0
            #IB   0 1060 600.0
        """)
        self.wizard.action_import_sie4()

        opening_move = self.env['account.move'].search([('company_id', '=', self.company_id.id)])
        # Line with account of code 99999 (undistributed P/L) should be added by default if the opening balance move is unbalanced
        self.assertSequenceEqual(opening_move.line_ids.mapped('balance'), (200.0, 600.0, -800.0))
        self.assertSequenceEqual(opening_move.line_ids.account_id.with_company(self.company_id).mapped('code'), ('1030', '1060', '999999'))

    def test_sie4_import_moves(self):
        """
        Ensure the imported moves are assigned a sequence name sorted by their date.
        """
        self.wizard.attachment_file = base64.b64encode(b"""
            #VER A 1 20240107 "1st item"
            {
                #TRANS 1060 {} 300.0
                #TRANS 2030 {} -300.0
            }
            #VER A 2 20240105 "2nd item"
            {
                #TRANS 1030 {} 100.0
                #TRANS 2019 {} -100.0
            }
            #VER A 3 20240106
            {
                #TRANS 1039 {} 200.0
                #TRANS 2020 {} -200.0
            }
        """)
        self.wizard.action_import_sie4()

        imported_moves = self.env['account.move'].search([('company_id', '=', self.company_id.id)])
        sorted_moves = imported_moves.sorted(key=lambda move: move.date)
        common_values = {
            'move_type': 'entry',
            'state': 'draft',
            'journal_id': self.journal_misc_id,
        }
        self.assertRecordValues(sorted_moves, [
            {'name': "MISC/2024/01/0001", 'ref': "Imported from SIE4 - 2nd item", 'date': fields.Date.from_string('2024-01-5'), **common_values},
            {'name': "MISC/2024/01/0002", 'ref': "Imported from SIE4", 'date': fields.Date.from_string('2024-01-6'), **common_values},
            {'name': "MISC/2024/01/0003", 'ref': "Imported from SIE4 - 1st item", 'date': fields.Date.from_string('2024-01-7'), **common_values},
        ])
        self.assertSequenceEqual(sorted_moves.line_ids.mapped('balance'), (100.0, -100.0, 200.0, -200.0, 300.0, -300.0))

    def test_sie4_import_move_with_tabs_instead_of_spaces(self):
        """ Ensure the imported moves with tabulations instead of spaces are correctly imported. """
        self.wizard.attachment_file = base64.b64encode(b"""
            #VER A 1 20240107 "item with tabs and spaces"
            {
                #TRANS\t1060\t{}\t300.0
                #TRANS\t2030 {} -300.0
            }
        """)
        self.wizard.action_import_sie4()

        imported_moves = self.env['account.move'].search([('company_id', '=', self.company_id.id)])
        self.assertRecordValues(
            imported_moves,
            [
                {
                    "name": "MISC/2024/01/0001",
                    "ref": "Imported from SIE4 - item with tabs and spaces",
                    "date": fields.Date.from_string("2024-01-07"),
                    "move_type": "entry",
                    "state": "draft",
                    "journal_id": self.journal_misc_id,
                }
            ],
        )
        self.assertSequenceEqual(imported_moves.line_ids.mapped("balance"), (300.0, -300.0))

    def test_sie4_import_move_with_several_objects_in_object_list(self):
        self.wizard.attachment_file = base64.b64encode(b"""
            #VER A 1 20240104 "move 1"
            {
                #TRANS 1060 {8 "204498" 10 "93425"} 100.0
                #TRANS 2030 {8 "204498" 10 "93425"} -100.0
            }
            #VER A 2 20240105 "move 2"
            {
                #TRANS 1030 {} 200.0
                #TRANS 2019 {8 "204498" 10 "93425"} -200.0
            }
            #VER A 3 20240106 "move 3"
            {
                #TRANS 1039 {8 "204498" 10 "93425"} 300.0
                #TRANS 2020 {} -300.0
            }
        """)
        self.wizard.action_import_sie4()

        imported_moves = self.env['account.move'].search([('company_id', '=', self.company_id.id)])
        common_values = {
            'move_type': 'entry',
            'state': 'draft',
            'journal_id': self.journal_misc_id,
        }
        self.assertRecordValues(imported_moves, [
            {'name': "MISC/2024/01/0003", 'ref': "Imported from SIE4 - move 3", 'date': fields.Date.from_string('2024-01-6'), **common_values},
            {'name': "MISC/2024/01/0002", 'ref': "Imported from SIE4 - move 2", 'date': fields.Date.from_string('2024-01-5'), **common_values},
            {'name': "MISC/2024/01/0001", 'ref': "Imported from SIE4 - move 1", 'date': fields.Date.from_string('2024-01-4'), **common_values},
        ])
        self.assertSequenceEqual(imported_moves.line_ids.mapped('balance'), (300.0, -300.0, 200.0, -200.0, 100.0, -100.0))

    def test_sie4_import_move_with_btrans_and_rtrans_transactions(self):
        """ Ensure the imported moves with BTRANS/RTRANS transactions only are not imported. """
        self.wizard.attachment_file = base64.b64encode(b"""
            #VER A 1 20240107 "item btrans"
            {
                #BTRANS 1060 {} 300.0
                #BTRANS 2030 {} -300.0
            }
            #VER A 2 20240107 "item rtrans"
            {
                #RTRANS 1060 {} 100.0
                #RTRANS 2030 {} -100.0
            }
        """)
        self.wizard.action_import_sie4()

        imported_moves = self.env['account.move'].search([('company_id', '=', self.company_id.id)])
        self.assertEqual(len(imported_moves), 0)

    # --------------------------------------------------------------------------
    # Import Key Algorithm Tests
    # --------------------------------------------------------------------------

    def test_sie4_import_key_rar(self):
        data_map = self.create_sie4_data_map()
        self.wizard._import_key_rar(data_map, '0', '20220101', '20221231')
        self.wizard._import_key_rar(data_map, '-1', '20210101', '20211231')

        self.assertDictEqual(data_map['dates'], {
            '-1': {'date_from': '2021-01-01', 'date_to': '2021-12-31'},
            '0': {'date_from': '2022-01-01', 'date_to': '2022-12-31'},
            '1': {'date_from': '2023-01-01', 'date_to': '2023-12-31'},
        })

    def test_sie4_import_key_konto(self):
        data_map = self.create_sie4_data_map()
        self.wizard._import_key_konto(data_map, '1001', 'item 1')
        self.wizard._import_key_konto(data_map, '1002', 'item 2')
        company_id = self.company_id.id
        self.assertDictEqual(data_map['account.account'], {
            'test.account_1001': {'company_ids': [company_id], 'code': '1001', 'name': 'item 1'},
            'test.account_1002': {'company_ids': [company_id], 'code': '1002', 'name': 'item 2'},
        })

    def test_sie4_import_key_ktyp(self):
        data_map = self.create_sie4_data_map()
        data_map['existing_accounts_map'] = {'1005': 999}
        self.wizard.update_account_data = False  # disable updating #KTYP for account 1005

        self.wizard._import_key_ktyp(data_map, '1001', 'T')
        self.wizard._import_key_ktyp(data_map, '1002', 'S')
        self.wizard._import_key_ktyp(data_map, '1003', 'K')
        self.wizard._import_key_ktyp(data_map, '1004', 'I')
        self.wizard._import_key_ktyp(data_map, '1005', 'T')  # should not appear in data_map['account.account']

        company_id = self.company_id.id
        self.assertDictEqual(data_map['account.account'], {
            'test.account_1001': {'company_ids': [company_id], 'code': '1001', 'account_type': "asset_receivable"},
            'test.account_1002': {'company_ids': [company_id], 'code': '1002', 'account_type': "liability_current"},
            'test.account_1003': {'company_ids': [company_id], 'code': '1003', 'account_type': "expense"},
            'test.account_1004': {'company_ids': [company_id], 'code': '1004', 'account_type': "income"},
        })

    def test_sie4_import_special_key_ver(self):
        data_map = self.create_sie4_data_map()
        self.wizard._import_special_key_ver(
            data_map=data_map,
            verification_str='sie4_20210105A1',
            verification_date='20210105',
            verification_text='',
            transactions=[
                {'account_code': '1910', 'balance': -195.0},
                {'account_code': '2641', 'balance': 20.88},
                {'account_code': '7690', 'balance': 74.12},
            ],
        )

        self.assertDictEqual(data_map['account.move'], {
            'test.move_sie4_20210105A1': {
                'company_id': self.company_id.id,
                'date': '2021-01-05',
                'journal_id': data_map['journal_misc_id'],
                'ref': "Imported from SIE4",
                'line_ids': [
                    Command.create({'account_id': 'test.account_1910', 'amount_currency': -195.0, 'currency_id': 18}),
                    Command.create({'account_id': 'test.account_2641', 'amount_currency': 20.88, 'currency_id': 18}),
                    Command.create({'account_id': 'test.account_7690', 'amount_currency': 74.12, 'currency_id': 18}),
                ],
            },
        })
