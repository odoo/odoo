# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields

from odoo.addons.account_payment.tests.common import AccountPaymentCommon
from odoo.addons.payment_custom.tests.common import PaymentCustomCommon


class SepaDirectDebitCommon(AccountPaymentCommon, PaymentCustomCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        cls.company.sdd_creditor_identifier = 'BE30ZZZ300D000000042'
        bank_ing = cls.env['res.bank'].create({'name': 'ING', 'bic': 'BBRUBEBB'})

        cls.sepa_bank_account = cls.env['res.partner.bank'].create({
            'acc_number': 'NL91 ABNA 0417 1643 00',
            'partner_id': cls.company.partner_id.id,
            'bank_id': bank_ing.id,
        })

        assert cls.sepa_bank_account.acc_type == 'iban'

        cls.sepa = cls._prepare_provider('sepa_direct_debit')
        cls.sepa_journal = cls.sepa.journal_id
        cls.sepa_journal.bank_account_id = cls.sepa_bank_account

        # create the partner bank account
        cls.partner_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'BE17412614919710',
            'partner_id': cls.partner.id,
            'company_id': cls.company.id,
        })

        cls.mandate = cls.env['sdd.mandate'].create({
            'partner_id': cls.partner.id,
            'company_id': cls.company.id,
            'partner_bank_id': cls.partner_bank.id,
            'start_date': fields.Date.today(),
            'payment_journal_id': cls.sepa_journal.id,
            'state': 'active',
        })

        cls.provider = cls.sepa
        cls.currency = cls.currency_euro
