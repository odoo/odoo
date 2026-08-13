# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from contextlib import contextmanager

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.payment.tests.common import PaymentCommon


class AccountPaymentCommon(PaymentCommon, AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dummy_provider_method = cls._create_dummy_payment_method_for_provider(
            provider=cls.dummy_provider,
            journal=cls.company_data['default_journal_bank'],
        )

        cls.account = cls.outbound_payment_method_line.payment_account_id
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'currency_id': cls.currency_euro.id,
            'partner_id': cls.partner.id,
            'line_ids': [
                (0, 0, {
                    'account_id': cls.account.id,
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 200.0,
                }),
                (0, 0, {
                    'account_id': cls.account.id,
                    'debit': 0.0,
                    'credit': 100.0,
                    'amount_currency': -200.0,
                }),
            ],
        })

        cls.provider.journal_id.inbound_payment_method_line_ids.filtered(lambda l: l.payment_provider_id == cls.provider).payment_account_id = cls.inbound_payment_method_line.payment_account_id

    def setUp(self):
        self.enable_post_process_patcher = False
        super().setUp()
