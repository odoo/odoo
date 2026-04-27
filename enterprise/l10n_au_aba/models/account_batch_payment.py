# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, api
from odoo.tools import float_round
from odoo.exceptions import UserError, RedirectWarning

import base64
import re
from datetime import datetime

SEPARATOR = '\r\n'


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    def _get_methods_generating_files(self):
        rslt = super(AccountBatchPayment, self)._get_methods_generating_files()
        rslt.append('aba_ct')
        return rslt

    @api.model
    def _check_valid_journal_for_aba(self, journal):
        bank_account = journal.bank_account_id
        if not bank_account:
            raise RedirectWarning(
                        message=_("The bank account on journal '%s' is not set. Please create a new account or set an existing one.", journal.name),
                        action=journal._get_records_action(name=_("Configure Journal"), target="new"),
                        button_text=_("Configure Journal Bank Account")
                    )
        if bank_account.acc_type != 'aba' or not bank_account.aba_bsb:
            raise RedirectWarning(
                message=_("The account %(account_number)s, of journal '%(journal_name)s', is not valid for ABA.\n"
                "Either its account number is incorrect or it has no BSB set.",
                account_number=bank_account.acc_number, journal_name=journal.name),
                action=bank_account._get_records_action(name=_("Configure Account"), target="new"),
                button_text=_("Configure Account")
            )
        if not journal.aba_fic or not journal.aba_user_spec or not journal.aba_user_number:
            raise RedirectWarning(
                        message=_("ABA fields for account '%(account_number)s', of journal '%(journal_name)s',"
                        "are not set. Please set the fields under ABA section!",
                        account_number=bank_account.acc_number, journal_name=journal.name),
                        action=journal._get_records_action(name=_("Configure Journal"), target="new"),
                        button_text=_("Configure Journal")
                    )

    def _check_payment_accounts_for_aba(self):
        self.ensure_one()
        faulty_accounts = self.payment_ids.partner_bank_id.filtered(
            lambda acc: acc.acc_type != "aba" or not acc.aba_bsb
        )
        if faulty_accounts:
            raise RedirectWarning(
                message=_("Following bank account(s) have invalid BSB or account number.\n%s",
                          "\n".join(faulty_accounts.mapped("name"))),
                action=faulty_accounts._get_records_action(name=_("Configure Bank Account(s)"), target="new"),
                button_text=_("Configure Bank Account(s)")
            )

    def _generate_export_file(self):
        self.ensure_one()
        if self.payment_method_code == 'aba_ct':
            self._check_valid_journal_for_aba(self.journal_id)
            self._check_payment_accounts_for_aba()

            aba_date = max(fields.Date.context_today(self), self.date).strftime('%d%m%y')
            aba_values = {
                'aba_date': aba_date,
                'aba_description': 'PAYMENTS',
                'self_balancing_reference': 'PAYMENTS %s' % aba_date,
                'payments_data': [{
                    'name': payment.name,
                    'amount': payment.amount,
                    'bank_account': payment.partner_bank_id,
                    'account_holder': payment.partner_id,
                    'transaction_code': '50',
                    'reference': payment.memo,
                } for payment in self.payment_ids]
            }

            return {
                'filename': 'ABA-' + self.journal_id.code + '-' + fields.Datetime.context_timestamp(self, datetime.now()).strftime("%Y%m%d%H%M") + '.aba',
                'file': base64.encodebytes(self._create_aba_document(self.journal_id, aba_values).encode()),
            }
        return super(AccountBatchPayment, self)._generate_export_file()

    @api.model
    def _create_aba_document(self, journal, aba_values):

        def _normalise_bsb(bsb):
            if not bsb:
                return ""
            test_bsb = re.sub(r'( |-)', '', bsb)
            return '%s-%s' % (test_bsb[0:3], test_bsb[3:6])

        def _to_fixed_width(string, length, fill=' ', right=False, check_utf8=False):
            utf8_length = length + (len(string) - len(string.encode('utf8'))) if check_utf8 else length
            return (right and string[0:utf8_length].rjust(utf8_length, fill)) or string[0:utf8_length].ljust(utf8_length, fill)

        def append_detail(detail_summary, detail_record, credit, debit):
            detail_summary['detail_records'].append(detail_record)
            if len(detail_summary['detail_records']) > 999997:
                raise UserError(_('Too many transactions for one ABA file - Please split in to multiple transfers'))
            detail_summary['credit_total'] += credit
            detail_summary['debit_total'] += debit
            if detail_summary['credit_total'] > 99999999.99 or detail_summary['debit_total'] > 99999999.99:
                raise UserError(_('The value of transactions is too high for one ABA file - Please split in to multiple transfers'))

        header_record = ''.join([
            '0',  # Always 0.
            (' ' * 17),  # Required to be filled with blank values.
            '01',  # Sequence Number.
            _to_fixed_width(journal.aba_fic, 3),  # Financial institution name.
            (' ' * 7),  # Required to be filled with blank values.
            _to_fixed_width(journal.aba_user_spec, 26),  # Name of User supplying file.
            _to_fixed_width(journal.aba_user_number, 6, fill='0', right=True),  # Number of User supplying file.
            _to_fixed_width(aba_values['aba_description'], 12),  # Description of the entries in the file.
            aba_values['aba_date'],  # Date to be processed.
            (' ' * 40),  # Required to be filled with blank values.
        ])

        detail_summary = {
            'detail_records': [],
            'credit_total': 0,
            'debit_total': 0,
        }

        aud = self.env["res.currency"].search([('name', '=', 'AUD')], limit=1)
        bank_account = journal.bank_account_id
        for record_data in aba_values['payments_data']:
            amount = float_round(record_data['amount'], 2)
            if amount > 99999999.99:
                raise UserError(_('Individual amount of payment %s is too high for ABA file - Please adjust', record_data['name']))

            detail_record = ''.join([
                '1',  # Record type, must be 1
                _normalise_bsb(record_data['bank_account'].aba_bsb),  # Bank/State/Branch number.
                _to_fixed_width(record_data['bank_account'].acc_number, 9, right=True),  # Account number to be credited or debited.
                record_data.get('indicator', ' '),  # Indicator, mostly used when paying withholding.
                record_data['transaction_code'],  # 13 for debit, 50 for credit.
                _to_fixed_width(str(round(aud.round(amount) * 100)), 10, '0', right=True),  # Amount in cents.
                _to_fixed_width(record_data['bank_account'].acc_holder_name or record_data['account_holder'].name, 32, check_utf8=True),  # Title of the account to be credited or debited.
                _to_fixed_width(record_data['reference'] or 'Payment', 18),  # Lodgement Reference.
                _normalise_bsb(bank_account.aba_bsb),  # BSB of the user to allow returns if necessary.
                _to_fixed_width(bank_account.acc_number, 9, right=True),  # Account number for the same reason.
                _to_fixed_width(bank_account.acc_holder_name or journal.company_id.name, 16, check_utf8=True),  # Account holder name for the same reason.
                ('0' * 8),  # Amount of tax withholding.
            ])
            # We do not support debit at the moment.
            append_detail(detail_summary, detail_record, amount, 0)

        if journal.aba_self_balancing:
            # self-balancing line use payment bank on both sides.
            debit = detail_summary['credit_total']
            # See above for lines description.
            detail_record = ''.join([
                '1',
                _normalise_bsb(bank_account.aba_bsb),
                _to_fixed_width(bank_account.acc_number, 9, right=True),
                ' ',
                '13',
                _to_fixed_width(str(round(aud.round(debit) * 100)), 10, fill='0', right=True),
                _to_fixed_width(bank_account.acc_holder_name or journal.company_id.name, 32, check_utf8=True),
                _to_fixed_width(aba_values['self_balancing_reference'], 18),
                _normalise_bsb(bank_account.aba_bsb),
                _to_fixed_width(bank_account.acc_number, 9, right=True),
                _to_fixed_width(bank_account.acc_holder_name or journal.company_id.name, 16, check_utf8=True),
                ('0' * 8),
            ])
            append_detail(detail_summary, detail_record, 0, debit)

        total = aud.round(abs(detail_summary['credit_total'] - detail_summary['debit_total'])) * 100
        credit_total = aud.round(detail_summary['credit_total']) * 100
        debit_total = aud.round(detail_summary['debit_total']) * 100
        footer_record = ''.join([
            '7',  # Record type, always 7
            '999-999',  # BSB format filler. Always '999-999'
            (' ' * 12),  # Required to be filled with blank values.
            _to_fixed_width(str(round(total)), 10, fill='0', right=True),  # Net total amount.
            _to_fixed_width(str(round(credit_total)), 10, fill='0', right=True),  # Credit total amount.
            _to_fixed_width(str(round(debit_total)), 10, fill='0', right=True),  # Debit total amount.
            (' ' * 24),  # Required to be filled with blank values.
            _to_fixed_width(str(len(detail_summary['detail_records'])), 6, fill='0', right=True),  # Amount of record of type 1.
            (' ' * 40),  # Required to be filled with blank values.
        ])

        return header_record + SEPARATOR + SEPARATOR.join(detail_summary['detail_records']) + SEPARATOR + footer_record + SEPARATOR
