# -*- coding: utf-8 -*-
from odoo.addons.account_accountant.tests.test_bank_rec_widget_common import TestBankRecWidgetCommon
from odoo.tests import tagged, HttpCase
from odoo import Command


@tagged('post_install', '-at_install')
class TestBankRecWidget(TestBankRecWidgetCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.st_line1 = cls._create_st_line(1000.0, payment_ref="line1", sequence=1)
        cls.st_line2 = cls._create_st_line(1000.0, payment_ref="line2", sequence=2)
        cls._create_st_line(1000.0, payment_ref="line3", sequence=3)
        cls._create_st_line(1000.0, payment_ref="line_credit", sequence=4, journal_id=cls.company_data['default_journal_credit'].id)

        # INV/2019/00001:
        cls._create_invoice_line(
            'out_invoice',
            partner_id=cls.partner_a.id,
            invoice_date='2019-01-01',
            invoice_line_ids=[{'price_unit': 1000.0}],
        )

        # INV/2019/00002:
        cls._create_invoice_line(
            'out_invoice',
            partner_id=cls.partner_a.id,
            invoice_date='2019-01-01',
            invoice_line_ids=[{'price_unit': 1000.0}],
        )

        cls.env['account.reconcile.model']\
            .search([('company_id', '=', cls.company_data['company'].id)])\
            .write({'past_months_limit': None})

        cls.reco_model_invoice = cls.env['account.reconcile.model'].create({
            'name': "test reconcile create invoice",
            'rule_type': 'writeoff_button',
            'counterpart_type': 'sale',
            'line_ids': [
                Command.create({'amount_string': '50'}),
                Command.create({'amount_string': '50'}),
            ],
        })

    def test_tour_bank_rec_widget(self):
        self.start_tour('/odoo', 'account_accountant_bank_rec_widget', login=self.env.user.login)

        self.assertRecordValues(self.st_line1.line_ids, [
            # pylint: disable=C0326
            {'account_id': self.st_line1.journal_id.default_account_id.id,      'balance': 1000.0,  'reconciled': False},
            {'account_id': self.company_data['default_account_receivable'].id,  'balance': -1000.0, 'reconciled': True},
        ])

        tax_account = self.company_data['default_tax_sale'].invoice_repartition_line_ids.account_id
        self.assertRecordValues(self.st_line2.line_ids, [
            # pylint: disable=C0326
            {'account_id': self.st_line2.journal_id.default_account_id.id,      'balance': 1000.0,  'tax_ids': []},
            {'account_id': self.company_data['default_account_payable'].id,     'balance': -869.57, 'tax_ids': self.company_data['default_tax_sale'].ids},
            {'account_id': tax_account.id,                                      'balance': -130.43, 'tax_ids': []},
        ])

    def test_tour_bank_rec_widget_ui(self):
        bank2 = self.env['account.journal'].create({
            'name': 'Bank2',
            'type': 'bank',
            'code': 'BNK2',
        })
        self._create_st_line(222.22, payment_ref="line4", sequence=4, journal_id=bank2.id)
        # INV/2019/00003:
        self._create_invoice_line(
            'out_invoice',
            partner_id=self.partner_a.id,
            invoice_date='2019-01-01',
            invoice_line_ids=[{'price_unit': 2000.0}],
        )
        self.st_line2.payment_ref = self.st_line2.payment_ref + ' - ' + 'INV/2019/00001'
        self.start_tour('/odoo?debug=assets', 'account_accountant_bank_rec_widget_ui', timeout=120, login=self.env.user.login)

    def test_tour_bank_rec_widget_rainbowman_reset(self):
        self.start_tour('/odoo?debug=assets', 'account_accountant_bank_rec_widget_rainbowman_reset', login=self.env.user.login)

    def test_tour_bank_rec_journal_items_export(self):
        self.start_tour('/web?debug=assets', 'account_accountant_journal_items_export', login=self.env.user.login)

    def test_tour_bank_rec_widget_statements(self):
        self.start_tour('/odoo?debug=assets', 'account_accountant_bank_rec_widget_statements', login=self.env.user.login)

    def test_tour_invoice_creation_from_reco_model(self):
        """ Test if move is created and added as a new_aml line in bank reconciliation widget """
        st_line = self._create_st_line(amount=1000, partner_id=self.partner_a.id)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        # The tour creates a move through reco model button, posts it, returns to widget and validates the move
        self.start_tour(
            '/odoo',
            'account_accountant_bank_rec_widget_reconciliation_button',
            login=self.env.user.login,
        )
        # Mount the validated statement line to confirm that information matches.
        wizard._js_action_mount_st_line(st_line.id)
        self.assertRecordValues(wizard.line_ids, [
            {'flag': 'liquidity',   'account_id': st_line.journal_id.default_account_id.id,             'balance': 1000},
            {'flag': 'aml',         'account_id': self.company_data['default_account_receivable'].id,   'balance': -1000},
        ])
        # Check that the aml comes from a move, and not from the auto-balance line
        self.assertTrue(wizard.line_ids[1].source_aml_move_id)

    def test_tour_invoice_creation_reco_model_currency(self):
        """ Test move creation through reconcile button when a foreign currency is used for the statement line """
        st_line = self._create_st_line(
            1800.0,
            date='2019-02-01',
            foreign_currency_id=self.other_currency.id,  # rate 2:1
            amount_currency=3600.0,
            partner_id=self.partner_a.id,
        )

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})

        self.start_tour(
            '/odoo',
            'account_accountant_bank_rec_widget_reconciliation_button',
            login=self.env.user.login,
        )
        # Mount the validated statement line to confirm that information matches.
        wizard._js_action_mount_st_line(st_line.id)

        # Move is created in the foreign currency, but in bank widget the balance appears in main currency.
        # If aml was created from the reco model button, display name matches payment_ref.
        self.assertRecordValues(wizard.line_ids, [
            {'flag': 'liquidity',   'balance': 1800,     'amount_currency': 1800},
            {'flag': 'aml',         'balance': -1800,    'amount_currency': -3600},
        ])
        # Confirm that the aml comes from a move, and not from the auto-balance line
        self.assertTrue(wizard.line_ids[1].source_aml_move_id)

    def test_tour_invoice_creation_combined_reco_model(self):
        """ Test creation of a move from a reconciliation model with different amount types """
        self.reco_model_invoice.name = "old test"  # rename previous reco model to be able to reuse the existing tour
        self.env['account.reconcile.model'].create({
            'name': "test reconcile combined",
            'rule_type': 'writeoff_button',
            'counterpart_type': 'purchase',
            'line_ids': [
                Command.create({
                    'amount_type': 'percentage_st_line',
                    'amount_string': '50',
                }),
                Command.create({
                    'amount_type': 'percentage',
                    'amount_string': '50',
                    'tax_ids': self.tax_purchase_b.ids,
                }),
                Command.create({
                    'amount_type': 'fixed',
                    'amount_string': '100',
                    'account_id': self.env.company.expense_currency_exchange_account_id.id,
                    'tax_ids': [Command.clear()]  # remove default tax added
                }),
                # Regex line will not be added to move, as the label of st line does not include digits
                Command.create({
                    'amount_type': 'regex',
                    'amount_string': r'BRT: ([\d,.]+)',
                }),
            ],
        })

        st_line = self._create_st_line(amount=-1000, partner_id=self.partner_a.id, payment_ref="combined test")
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        # The tour creates a move through reco model button, posts it, returns to widget and validates the move
        self.start_tour(
            '/odoo',
            'account_accountant_bank_rec_widget_reconciliation_button',
            login=self.env.user.login,
        )
        # Mount the validated statement line to confirm that widget line matches created move and balance line is added.
        wizard._js_action_mount_st_line(st_line.id)
        self.assertRecordValues(wizard.line_ids, [
            {'flag': 'liquidity',   'account_id': st_line.journal_id.default_account_id.id,          'balance': -1000},
            {'flag': 'aml',         'account_id': self.company_data['default_account_payable'].id,   'balance': 850},
            {'flag': 'aml',         'account_id': self.company_data['default_account_payable'].id,   'balance': 150},
        ])
        # Check that the aml comes from an existing move
        move = wizard.line_ids[1].source_aml_move_id
        self.assertTrue(move)

        # The total price of these lines should match the percentage or fixed amount of reco model lines
        self.assertRecordValues(move.line_ids, [
            # 50% of statement line (of 1000.0)
            {'price_total': 500,   'debit': 434.78,   'credit': 0,     'name': 'combined test',   'account_id': self.company_data['default_account_expense'].id},
            # 50% of balance (of residual value = 500.0)
            {'price_total': 250,   'debit': 217.39,   'credit': 0,     'name': 'combined test',   'account_id': self.company_data['default_account_expense'].id},
            # fixed amount of 100.0, no tax in reco model line
            {'price_total': 100,   'debit': 100,      'credit': 0,     'name': 'combined test',   'account_id': self.env.company.expense_currency_exchange_account_id.id},
            # Tax for line 1 (65.22 + 434.78 = 500)
            {'price_total': 0,     'debit': 65.22,    'credit': 0,     'name': '15%',             'account_id': self.company_data['default_account_tax_purchase'].id},
            # Tax for line 1 (32.61 + 217.39 = 250)
            {'price_total': 0,     'debit': 32.61,    'credit': 0,     'name': '15% (Copy)',      'account_id': self.company_data['default_account_tax_purchase'].id},
            {'price_total': 0,     'debit': 0,        'credit': 850,   'name': 'combined test',   'account_id': self.company_data['default_account_payable'].id},
        ])

    def test_analytic_distribution_saved(self):
        """
        Test that the analytic distribution is saved when it is changed on the account.move.line in the banc rec
        """
        analytic_plan = self.env['account.analytic.plan'].create({
            'name': 'Default',
            'sequence': 1, # Used to simplify analytic distribution selector during the tour
        })
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'analytic_account',
            'plan_id': analytic_plan.id,
            'company_id': False,
        })
        self.env.user.write({'groups_id': [Command.link(self.env.ref('analytic.group_analytic_accounting').id)]})
        self.start_tour('/web', 'account_accountant_bank_rec_widget_save_analytic_distribution', login=self.env.user.login)
        line1 = self.env['account.move.line'].search([('name', '=', 'line1')], limit=1)
        self.assertEqual(line1.analytic_distribution, {str(analytic_account.id): 100})
