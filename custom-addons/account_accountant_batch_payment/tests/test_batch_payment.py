# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestBatchPayment(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Create a bank journal
        cls.journal = cls.company_data['default_journal_bank']
        cls.batch_deposit_method = cls.env.ref('account_batch_payment.account_payment_method_batch_deposit')
        cls.batch_deposit = cls.journal.inbound_payment_method_line_ids.filtered(lambda l: l.code == 'batch_payment')

    @classmethod
    def createPayment(cls, partner, amount):
        """ Create a batch deposit payment """
        payment = cls.env['account.payment'].create({
            'journal_id': cls.journal.id,
            'payment_method_line_id': cls.batch_deposit.id,
            'payment_type': 'inbound',
            'date': time.strftime('%Y') + '-07-15',
            'amount': amount,
            'partner_id': partner.id,
            'partner_type': 'customer',
        })
        payment.action_post()
        return payment

    def test_zero_amount_payment(self):
        zero_payment = self.createPayment(self.partner_a, 0)
        batch_vals = {
            'journal_id': self.journal.id,
            'payment_ids': [(4, zero_payment.id, None)],
            'payment_method_id': self.batch_deposit_method.id,
        }
        self.assertRaises(ValidationError, self.env['account.batch.payment'].create, batch_vals)
