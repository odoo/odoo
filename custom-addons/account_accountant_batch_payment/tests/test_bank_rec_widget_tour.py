# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account_accountant.tests.test_bank_rec_widget_common import TestBankRecWidgetCommon
from odoo.tests import tagged, HttpCase


@tagged('post_install', '-at_install')
class TestBankRecWidget(TestBankRecWidgetCommon, HttpCase):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.env['account.reconcile.model']\
            .search([('company_id', '=', cls.company_data['company'].id)])\
            .write({'past_months_limit': None})

    def test_tour_bank_rec_widget(self):
        self._create_st_line(500.0, payment_ref="line1", sequence=1)
        self._create_st_line(100.0, payment_ref="line2", sequence=2)
        self._create_st_line(100.0, payment_ref="line3", sequence=3)

        payment_method_line = self.company_data['default_journal_bank'].inbound_payment_method_line_ids\
            .filtered(lambda l: l.code == 'batch_payment')

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

        self.env['account.batch.payment'].create({
            'name': "BATCH0001",
            'date': '2020-01-01',
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payments.ids)],
            'payment_method_id': payment_method_line.payment_method_id.id,
        })

        self.start_tour('/web', 'account_accountant_batch_payment_bank_rec_widget', login=self.env.user.login)
