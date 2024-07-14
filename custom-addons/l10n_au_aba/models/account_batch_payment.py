# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.tools import float_round
from odoo.exceptions import UserError

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

    def _generate_export_file(self):
        self.ensure_one()
        if self.payment_method_code == 'aba_ct':
            bank_account = self.journal_id.bank_account_id
            if bank_account.acc_type != 'aba' or not bank_account.aba_bsb:
                raise UserError(_("The account %s, of journal '%s', is not valid for ABA.\nEither its account number is incorrect or it has no BSB set.", bank_account.acc_number, self.journal_id.name))

            if not self.journal_id.aba_fic or not self.journal_id.aba_user_spec or not self.journal_id.aba_user_number:
                raise UserError(_("The account %s, of journal '%s', is not set up for ABA payments.\nPlease fill in its ABA fields.", bank_account.acc_number, self.journal_id.name))

            for payment in self.payment_ids:
                if payment.partner_bank_id.acc_type != 'aba' or not payment.partner_bank_id.aba_bsb:
                    raise UserError(_("Bank account for payment '%s' has an invalid BSB or account number.", payment.name))

            return {
                'filename': 'ABA-' + self.journal_id.code + '-' + fields.Datetime.context_timestamp(self, datetime.now()).strftime("%Y%m%d%H%M") + '.aba',
                'file': base64.encodebytes(self._create_aba_document().encode()),
            }
        return super(AccountBatchPayment, self)._generate_export_file()

    def _create_aba_document(self):
        def _normalise_bsb(bsb):
            if not bsb:
                return ""
            test_bsb = re.sub('( |-)','',bsb)
            return '%s-%s' % (test_bsb[0:3],test_bsb[3:6])

        def to_fixed_width(string, length, fill=' ', right=False):
            return right and string[0:length].rjust(length, fill) or string[0:length].ljust(length, fill)

        def append_detail(detail_summary, detail_record, credit, debit):
            detail_summary['detail_records'].append(detail_record)
            if len(detail_summary['detail_records']) > 999997:
                raise UserError(_('Too many transactions for one ABA file - Please split in to multiple transfers'))
            detail_summary['credit_total'] += credit
            detail_summary['debit_total'] += debit
            if detail_summary['credit_total'] > 99999999.99 or detail_summary['debit_total'] > 99999999.99:
                raise UserError(_('The value of transactions is too high for one ABA file - Please split in to multiple transfers'))

        aba_date = max(fields.Date.context_today(self), self.date)
        header_record = '0' + (' ' * 17) + '01' \
                + to_fixed_width(self.journal_id.aba_fic, 3) \
                + (' ' * 7) \
                + to_fixed_width(self.journal_id.aba_user_spec, 26) \
                + to_fixed_width(self.journal_id.aba_user_number, 6, fill='0', right=True) \
                + to_fixed_width('PAYMENTS',12) \
                + aba_date.strftime('%d%m%y') \
                + (' ' * 40)

        detail_summary = {
            'detail_records': [],
            'credit_total': 0,
            'debit_total': 0,
            }

        aud_currency = self.env["res.currency"].search([('name', '=', 'AUD')], limit=1)
        bank_account = self.journal_id.bank_account_id
        for payment in self.payment_ids:
            credit = float_round(payment.amount, 2)
            debit = 0
            if credit > 99999999.99 or debit > 99999999.99:
                raise UserError(_('Individual amount of payment %s is too high for ABA file - Please adjust', payment.name))
            detail_record = '1' \
                    + _normalise_bsb(payment.partner_bank_id.aba_bsb) \
                    + to_fixed_width(payment.partner_bank_id.acc_number, 9, right=True) \
                    + ' ' + '50' \
                    + to_fixed_width(str(round(aud_currency.round(credit) * 100)), 10, '0', right=True) \
                    + to_fixed_width(payment.partner_bank_id.acc_holder_name or payment.partner_id.name, 32) \
                    + to_fixed_width(payment.ref or 'Payment', 18) \
                    + _normalise_bsb(bank_account.aba_bsb) \
                    + to_fixed_width(bank_account.acc_number, 9, right=True) \
                    + to_fixed_width(bank_account.acc_holder_name or self.journal_id.company_id.name, 16) \
                    + ('0' * 8)
            append_detail(detail_summary, detail_record, credit, debit)

        if self.journal_id.aba_self_balancing:
            # self balancing line use payment bank on both sides.
            credit = 0
            debit = detail_summary['credit_total']
            aba_date = max(fields.Date.context_today(self), self.date)
            detail_record = '1' \
                    + _normalise_bsb(bank_account.aba_bsb) \
                    + to_fixed_width(bank_account.acc_number, 9, right=True) \
                    + ' ' + '13' \
                    + to_fixed_width(str(round(aud_currency.round(debit) * 100)), 10, fill='0', right=True) \
                    + to_fixed_width(bank_account.acc_holder_name or self.journal_id.company_id.name, 32) \
                    + to_fixed_width('PAYMENTS %s' % aba_date.strftime('%d%m%y'), 18) \
                    + _normalise_bsb(bank_account.aba_bsb) \
                    + to_fixed_width(bank_account.acc_number, 9, right=True) \
                    + to_fixed_width(bank_account.acc_holder_name or self.journal_id.company_id.name, 16) \
                    + ('0' * 8)
            append_detail(detail_summary, detail_record, credit, debit)

        footer_record = '7' + '999-999' + (' ' * 12) \
                + to_fixed_width(str(round(aud_currency.round(abs(detail_summary['credit_total'] - detail_summary['debit_total'])) * 100)), 10, fill='0', right=True) \
                + to_fixed_width(str(round(aud_currency.round(detail_summary['credit_total']) * 100)), 10, fill='0', right=True) \
                + to_fixed_width(str(round(aud_currency.round(detail_summary['debit_total']) * 100)), 10, fill='0', right=True) \
                + (' ' * 24) \
                + to_fixed_width(str(len(detail_summary['detail_records'])), 6, fill='0', right=True) \
                + (' ' * 40)

        return header_record + SEPARATOR + SEPARATOR.join(detail_summary['detail_records']) + SEPARATOR + footer_record + SEPARATOR
