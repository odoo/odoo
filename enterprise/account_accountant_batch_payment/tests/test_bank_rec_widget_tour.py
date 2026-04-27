# -*- coding: utf-8 -*-
from odoo import Command
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestMockOnlineSyncCommon
from odoo.addons.account_accountant.tests.test_bank_rec_widget_common import TestBankRecWidgetCommon


@tagged('post_install', '-at_install')
class TestBankRecWidgetTour(TestBankRecWidgetCommon, AccountTestMockOnlineSyncCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['account.reconcile.model']\
            .search([('company_id', '=', cls.company.id)])\
            .write({'past_months_limit': None})

    def test_tour_bank_rec_widget(self):
        self._create_st_line(500.0, payment_ref="line1", sequence=1)
        self._create_st_line(100.0, payment_ref="line2", sequence=2)
        self._create_st_line(100.0, payment_ref="line3", sequence=3)
        self._create_st_line(1000.0, payment_ref="line_credit", sequence=4, journal_id=self.company_data['default_journal_credit'].id)

        payment_method_line = self.company_data['default_journal_bank'].inbound_payment_method_line_ids\
            .filtered(lambda l: l.code == 'batch_payment')
        payment_method_line.payment_account_id = self.inbound_payment_method_line.payment_account_id

        payments = self.env['account.payment'].create([
            {
                'date': '2020-01-01',
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': self.partner_a.id,
                'payment_method_line_id': payment_method_line.id,
                'amount': i * 100.0,
            }
            for i in range(1, 4)
        ])
        payments.action_post()

        batch = self.env['account.batch.payment'].create({
            'name': "BATCH0001",
            'date': '2020-01-01',
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payments.ids)],
            'payment_method_id': payment_method_line.payment_method_id.id,
        })
        batch.validate_batch()

        self.start_tour('/odoo', 'account_accountant_batch_payment_bank_rec_widget', login=self.env.user.login)

    def test_batch_line_clickable(self):
        self._create_st_line(500.0, payment_ref="line1", sequence=1)

        payments = self.env['account.payment'].create([
            {
                'date': '2020-01-01',
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': self.partner_a.id,
                'amount': i * 100.0,
            }
            for i in range(1, 3)
        ])
        payments.action_post()

        batch = self.env['account.batch.payment'].create({
            'name': "BATCH0001",
            'date': '2020-01-01',
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payments.ids)],
        })
        self.env.user.write({'groups_id': [Command.link(self.env.ref('analytic.group_analytic_accounting').id)]})

        batch.validate_batch()

        self.start_tour('/odoo', 'account_accountant_batch_payment_bank_rec_widget_batch_line_clickable', login=self.env.user.login)
