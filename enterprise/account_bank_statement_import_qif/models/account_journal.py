# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import logging

import dateutil.parser

from odoo import fields, models, _
from odoo.exceptions import UserError


logger = logging.getLogger(__name__)

DATE_OF_TRANSACTION = b'D'
TOTAL_AMOUNT = b'T'
CHECK_NUMBER = b'N'
PAYEE = b'P'
MEMO = b'M'
END_OF_ITEM = b'^'


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    qif_decimal_point = fields.Char(
        string="QIF Decimal Separator",
        default='.',
        help="Field used to avoid conversion issues.",
    )
    qif_date_format = fields.Selection(
        selection=[
            ('month_first', "mm/dd/yy"),
            ('day_first', "dd/mm/yy"),
        ],
        default='day_first',
        string='QIF Dates format',
        help="Although the historic QIF date format is month-first (mm/dd/yy), many financial institutions use the local format."
             "Therefore, it is frequent outside the US to have QIF date formatted day-first (dd/mm/yy).",
    )

    def _get_bank_statements_available_import_formats(self):
        rslt = super(AccountJournal, self)._get_bank_statements_available_import_formats()
        rslt.append('QIF')
        return rslt

    def _check_qif(self, attachment):
        return (attachment.raw or b'').strip().startswith(b'!Type:')

    def _parse_bank_statement_file(self, attachment):
        if not self._check_qif(attachment):
            return super()._parse_bank_statement_file(attachment)

        data_list = [
            line.rstrip(b'\r\n')
            for line in io.BytesIO(attachment.raw.strip())
        ]
        try:
            header = data_list[0].strip().split(b':')[1]
        except:
            raise UserError(_('Could not decipher the QIF file.'))

        transactions = []
        vals_line = {'payment_ref': []}
        total = 0.0
        # Identified header types of the QIF format that we support.
        # Other types might need to be added. Here are the possible values
        # according to the QIF spec: Cash, Bank, CCard, Invst, Oth A, Oth L, Invoice.
        if header in [b'Bank', b'Cash', b'CCard']:
            vals_bank_statement = {}
            for line in data_list:
                line = line.strip()
                if not line:
                    continue
                vals_line['sequence'] = len(transactions) + 1
                data = line[1:]
                if line[:1] == DATE_OF_TRANSACTION:
                    dayfirst = self.qif_date_format == 'day_first'
                    vals_line['date'] = dateutil.parser.parse(data, fuzzy=True, dayfirst=dayfirst).date()
                elif line[:1] == TOTAL_AMOUNT:
                    amount = float(data.replace(b',', b'.' if self.qif_decimal_point == ',' else b''))
                    total += amount
                    vals_line['amount'] = amount
                elif line[:1] == CHECK_NUMBER:
                    vals_line['ref'] = data.decode()
                elif line[:1] == PAYEE:
                    name = data.decode()
                    vals_line['payment_ref'].append(name)
                    # Since QIF doesn't provide account numbers, we'll have to find res.partner and res.partner.bank here
                    # (normal behavious is to provide 'account_number', which the generic module uses to find partner/bank)
                    partner_bank = self.env['res.partner.bank'].search([('partner_id.name', '=', name)], limit=1)
                    if partner_bank:
                        vals_line['partner_bank_id'] = partner_bank.id
                        vals_line['partner_id'] = partner_bank.partner_id.id
                elif line[:1] == MEMO:
                    vals_line['payment_ref'].append(data.decode())
                elif line[:1] == END_OF_ITEM:
                    if vals_line['payment_ref']:
                        vals_line['payment_ref'] = u': '.join(vals_line['payment_ref'])
                    else:
                        del vals_line['payment_ref']
                    transactions.append(vals_line)
                    vals_line = {'payment_ref': []}
                elif line[:1] == b'\n':
                    transactions = []
        else:
            raise UserError(_('This file is either not a bank statement or is not correctly formed.'))

        vals_bank_statement.update({
            'balance_end_real': total,
            'transactions': transactions
        })
        return None, None, [vals_bank_statement]
