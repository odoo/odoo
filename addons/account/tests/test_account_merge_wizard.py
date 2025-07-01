from odoo import Command
from odoo.addons.account.tests.common import TestAccountMergeCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountMergeWizard(TestAccountMergeCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()

        cls.company_1 = cls.company_data['company']
        cls.company_2 = cls.company_data_2['company']
        cls.accounts = cls.env['account.account']._load_records([
            {
                'xml_id': f'account.{cls.company_1.id}_test_account_1',
                'values': {
                    'name': 'My First Account',
                    'code': '100234',
                    'account_type': 'asset_receivable',
                    'company_ids': [Command.link(cls.company_1.id)],
                    'tax_ids': [Command.link(cls.company_data['default_tax_sale'].id)],
                    'tag_ids': [Command.link(cls.env.ref('account.account_tag_operating').id)],
                },
            },
            {
                'xml_id': f'account.{cls.company_1.id}_test_account_2',
                'values': {
                    'name': 'My Second Account',
                    'code': '100235',
                    'account_type': 'liability_payable',
                    'company_ids': [Command.link(cls.company_1.id)],
                    'tax_ids': [Command.link(cls.company_data['default_tax_sale'].id)],
                    'tag_ids': [Command.link(cls.env.ref('account.account_tag_operating').id)],
                },
            },
            {
                'xml_id': f'account.{cls.company_2.id}_test_account_3',
                'values': {
                    'name': 'My Third Account',
                    'code': '100236',
                    'account_type': 'asset_receivable',
                    'company_ids': [Command.link(cls.company_2.id)],
                    'tax_ids': [Command.link(cls.company_data_2['default_tax_sale'].id)],
                    'tag_ids': [Command.link(cls.env.ref('account.account_tag_investing').id)],
                },
            },
            {
                'xml_id': f'account.{cls.company_2.id}_test_account_4',
                'values': {
                    'name': 'My Fourth Account',
                    'code': '100237',
                    'account_type': 'liability_payable',
                    'company_ids': [Command.link(cls.company_2.id)],
                    'tax_ids': [Command.link(cls.company_data_2['default_tax_sale'].id)],
                    'tag_ids': [Command.link(cls.env.ref('account.account_tag_investing').id)],
                },
            }
        ])

    def _create_hashed_move(self, account, company_data):
        hashed_move = self.env['account.move'].create([
            {
                'journal_id': company_data['default_journal_sale'].id,
                'date': '2024-07-20',
                'line_ids': [
                    Command.create({
                        'account_id': account.id,
                        'balance': 10.0,
                    }),
                    Command.create({
                        'account_id': company_data['default_account_receivable'].id,
                        'balance': -10.0,
                    })
                ]
            },
        ])
        hashed_move.action_post()
        company_data['default_journal_sale'].restrict_mode_hash_table = True
        hashed_move.button_hash()

    def test_merge(self):
        """ Check that you can merge accounts. """
        # 1. Set-up various fields pointing to the accounts to merge
        referencing_records = {
            account: self._create_references_to_account(account)
            for account in self.accounts
        }

        # Also set up different names for the accounts in various languages
        self.env['res.lang']._activate_lang('fr_FR')
        self.env['res.lang']._activate_lang('nl_NL')
        self.accounts[0].with_context({'lang': 'fr_FR'}).name = "Mon premier compte"
        self.accounts[2].with_context({'lang': 'fr_FR'}).name = "Mon troisième compte"
        self.accounts[2].with_context({'lang': 'nl_NL'}).name = "Mijn derde conto"

        # 2. Check that the merge wizard groups accounts 1 and 3 together, and accounts 2 and 4 together.
        wizard = self._create_account_merge_wizard(self.accounts)
        expected_wizard_line_vals = [
            {
                'display_type': 'line_section',
                'account_id': self.accounts[0].id,
                'info': 'Trade Receivable (Reconcilable)',
            },
            {
                'display_type': 'account',
                'account_id': self.accounts[0].id,
                'info': False,
            },
            {
                'display_type': 'account',
                'account_id': self.accounts[2].id,
                'info': False,
            },
            {
                'display_type': 'line_section',
                'account_id': self.accounts[1].id,
                'info': 'Trade Payable (Reconcilable)',
            },
            {
                'display_type': 'account',
                'account_id': self.accounts[1].id,
                'info': False,
            },
            {
                'display_type': 'account',
                'account_id': self.accounts[3].id,
                'info': False,
            },
        ]

        self.assertRecordValues(wizard.wizard_line_ids, expected_wizard_line_vals)

        # 3. Perform the merge
        wizard.action_merge()

        # 4. Check that the accounts other than the ones to merge into are deleted.
        self.assertFalse(self.accounts[2:].exists())

        # 5. Check that the company_ids and codes are correctly merged.
        self.assertRecordValues(
            self.accounts[:2],
            [
                {
                    'company_ids': [self.company_1.id, self.company_2.id],
                    'name': 'My First Account',
                    'code': '100234',
                    'tax_ids': [self.company_data['default_tax_sale'].id, self.company_data_2['default_tax_sale'].id],
                    'tag_ids': [self.env.ref('account.account_tag_operating').id, self.env.ref('account.account_tag_investing').id],
                },
                {
                    'company_ids': [self.company_1.id, self.company_2.id],
                    'name': 'My Second Account',
                    'code': '100235',
                    'tax_ids': [self.company_data['default_tax_sale'].id, self.company_data_2['default_tax_sale'].id],
                    'tag_ids': [self.env.ref('account.account_tag_operating').id, self.env.ref('account.account_tag_investing').id],
                }
            ]
        )
        self.assertRecordValues(
            self.accounts[:2].with_company(self.company_2),
            [{'code': '100236'}, {'code': '100237'}]
        )

        # 6. Check that references to the accounts are merged correctly
        merged_account_by_account = {
            self.accounts[0]: self.accounts[0],
            self.accounts[1]: self.accounts[1],
            self.accounts[2]: self.accounts[0],
            self.accounts[3]: self.accounts[1],
        }
        for account, referencing_records_for_account in referencing_records.items():
            expected_account = merged_account_by_account[account]
            for referencing_record, fname in referencing_records_for_account.items():
                expected_field_value = expected_account.ids if referencing_record._fields[fname].type == 'many2many' else expected_account.id
                self.assertRecordValues(referencing_record, [{fname: expected_field_value}])

        # 7. Check that the xmlids are preserved
        self.assertEqual(self.env['account.chart.template'].ref('test_account_1'), self.accounts[0])
        self.assertEqual(self.env['account.chart.template'].ref('test_account_2'), self.accounts[1])
        self.assertEqual(self.env['account.chart.template'].with_company(self.company_2).ref('test_account_3'), self.accounts[0])
        self.assertEqual(self.env['account.chart.template'].with_company(self.company_2).ref('test_account_4'), self.accounts[1])

        # 8. Check that the name translations are merged correctly
        self.assertRecordValues(self.accounts[0].with_context({'lang': 'fr_FR'}), [{'name': "Mon premier compte"}])
        self.assertRecordValues(self.accounts[0].with_context({'lang': 'nl_NL'}), [{'name': "Mijn derde conto"}])

    def test_cannot_merge_same_company(self):
        """ Check that you cannot merge two accounts belonging to the same company. """
        self.accounts[1].account_type = 'asset_receivable'

        wizard = self._create_account_merge_wizard(self.accounts[:2])

        expected_wizard_line_vals = [
            {
                'display_type': 'line_section',
                'account_id': self.accounts[0].id,
                'info': 'Trade Receivable (Reconcilable)',
            },
            {
                'display_type': 'account',
                'account_id': self.accounts[0].id,
                'info': False,
            },
            {
                'display_type': 'account',
                'account_id': self.accounts[1].id,
                'info': "Belongs to the same company as 100234 My First Account.",
            },
        ]

        self.assertRecordValues(wizard.wizard_line_ids, expected_wizard_line_vals)

    def test_can_merge_accounts_if_one_is_hashed(self):
        """ Check that you can merge two accounts if only one is hashed, but that the hashed account's ID is preserved. """

        # 1. Create hashed move and check that the wizard has no errors
        self._create_hashed_move(self.accounts[2], self.company_data_2)
        wizard = self._create_account_merge_wizard(self.accounts[0] | self.accounts[2])

        expected_wizard_line_vals = [
            {
                'display_type': 'line_section',
                'account_id': self.accounts[0].id,
                'info': 'Trade Receivable (Reconcilable)',
            },
            {
                'display_type': 'account',
                'account_id': self.accounts[0].id,
                'info': False,
            },
            {
                'display_type': 'account',
                'account_id': self.accounts[2].id,
                'info': False,
            },
        ]

        self.assertRecordValues(wizard.wizard_line_ids, expected_wizard_line_vals)

        # 2. Perform the merge
        wizard.action_merge()

        # 3. Check that the non-hashed account is deleted.
        self.assertFalse(self.accounts[0].exists())

    def test_cannot_merge_two_hashed_accounts(self):
        """ Check that you cannot merge two accounts if both are hashed. """
        self._create_hashed_move(self.accounts[0], self.company_data)
        self._create_hashed_move(self.accounts[2], self.company_data_2)

        wizard = self._create_account_merge_wizard(self.accounts[0] | self.accounts[2])

        expected_wizard_line_vals = [
            {
                'display_type': 'line_section',
                'account_id': self.accounts[0].id,
                'info': 'Trade Receivable (Reconcilable)',
            },
            {
                'display_type': 'account',
                'account_id': self.accounts[0].id,
                'info': False,
            },
            {
                'display_type': 'account',
                'account_id': self.accounts[2].id,
                'info': "Contains hashed entries, but 100234 My First Account also has hashed entries.",
            },
        ]

        self.assertRecordValues(wizard.wizard_line_ids, expected_wizard_line_vals)

    def test_merge_accounts_company_dependent_related(self):
        payable_accounts = self.env['account.account'].search([('name', '=', 'Account Payable')])
        self.assertEqual(len(payable_accounts), 2)
        wizard = self._create_account_merge_wizard(payable_accounts)
        wizard.action_merge()
        payable_accounts = self.env['account.account'].search([('name', '=', 'Account Payable')])
        self.assertEqual(len(payable_accounts), 1)
        for company in self.env.companies:
            partner_payable_account = self.partner_a.with_company(company).property_account_payable_id.exists()
            self.assertEqual(partner_payable_account, payable_accounts)
