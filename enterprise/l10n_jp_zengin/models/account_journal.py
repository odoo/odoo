# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib
import re
from datetime import datetime

from odoo import _, fields, models
from odoo.tools import plaintext2html
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_jp_zengin_merge_transactions = fields.Boolean(
        string="Merge Transactions",
        help="Merge collective payments for Zengin files",
    )

    def _default_outbound_payment_methods(self):
        res = super()._default_outbound_payment_methods()
        if self._is_payment_method_available("zengin"):
            res |= self.env.ref('l10n_jp_zengin.account_payment_method_zengin_outbound')
        return res

    def _get_bank_statements_available_import_formats(self):
        rslt = super()._get_bank_statements_available_import_formats()
        rslt.append('ZENGIN')
        return rslt

    def _check_zengin(self, zengin_string):
        # Match the first 59 characters of the Zengin file, as defined by the zengin specifications
        allowed_chars = r'[ 0-9A-Z\uFF5F-\uFF9F\\,./()-]'
        pattern = (
            r'10[13]0\d{6}\d{6}\d{6}\d{4}'
            + allowed_chars + r'{15}'
            + r'\d{3}'
            + allowed_chars + r'{15}'
        )
        return re.match(pattern, zengin_string) is not None

    def _parse_bank_statement_file(self, attachment):
        record_data = False
        with contextlib.suppress(UnicodeDecodeError):
            record_data = attachment.raw.decode('SHIFT_JIS')  # Zengin files are encoded in SHIFT_JIS

        if not record_data or not self._check_zengin(record_data):
            return super()._parse_bank_statement_file(attachment)
        return self._parse_bank_statement_file_zengin(record_data)

    def _parse_bank_statement_file_zengin(self, record_data):
        def rmspaces(s):
            return s.strip()

        def parsedate(s):
            # Zengin has only 10 years of data, so any year before 26 is in the Reiwa era.
            # The Reiwa era starts from 1st May 2019.
            # The Heisei era starts from 8th January 1989 and ends on 30th April 2019.
            # Japanese years are counted from 1.
            # Examples:
            # - 260101 -> 2014-01-01 (Heisei 26)
            # - 010501 -> 2019-05-01 (Reiwa 1)
            def parse_japanese_year(dy):
                return dy + 2019 - 1 if dy < 26 else dy + 1989 - 1
            dt = str(parse_japanese_year(int(s[0:2].lstrip('0')))) + s[2:6]
            return datetime.strptime(dt, '%Y%m%d').strftime('%Y-%m-%d')

        def parse_header(env, line):
            result = {
                'date': parsedate(line[10:16]),
            }
            if line[1:3] == '01':
                if len(line) != 199:
                    raise UserError(env._('Incorrect header length: %(length)s', length=len(line)))
                statement_type = 'transfer'
                acc_number = line[60:67]
                result['name'] = env._("Zengin Transfer - %(date)s", date=parsedate(line[10:16]))
            else:
                if len(line) != 200:
                    raise UserError(env._('Incorrect header length: %(length)s', length=len(line)))
                statement_type = 'deposit_withdrawal'
                acc_number = line[66:73]
                result['name'] = env._("Zengin Deposit/Withdrawal - %(date)s", date=parsedate(line[10:16]))
                if balance_start := rmspaces(line[115:129]):
                    result['balance_start'] = float(balance_start)
            return statement_type, acc_number, result

        def get_transfer_note(env, line, exceed_amount: bool):
            note = [
                env._('Bank Name: %(bank)s', bank=rmspaces(line[97:112])),
                env._('Branch Name: %(branch)s', branch=rmspaces(line[112:127])),
            ]
            if edi_info := rmspaces(line[128:148]) if exceed_amount else rmspaces(line[152:172]):
                note.append(env._('EDI Information: %(info)s', info=edi_info))
            return note

        def get_deposit_withdrawal_note(env, line, deposit_type):
            transaction_category_map = {
                '10': env._('Cash'),
                '11': env._('Transfer'),
                '12': env._('Deposit'),
                '13': env._('Exchange'),
                '14': env._('Transfer'),
                '18': env._('Other'),
            }
            bill_type_map = {
                '1': env._('Check'),
                '2': env._('Promissory Note'),
                '3': env._('Bill of Exchange'),
            }
            note = []
            note.append(env._('Transaction Category: %(category)s', category=transaction_category_map.get(line[22:24], env._('Unknown'))))
            if bill_type := rmspaces(line[60:61]):
                note.extend([
                    env._('Bill Type: %(type)s', type=bill_type_map.get(bill_type, env._('Unknown'))),
                    env._('Bill Number: %(id)s', id=rmspaces(line[61:68])),
                ])
            if deposit_type in ['regular', 'current', 'savings']:
                if sending_bank := rmspaces(line[129:144]):
                    note.append(env._('Sending Bank: %(bank)s', bank=sending_bank))
                if sending_bank_branch := rmspaces(line[144:159]):
                    note.append(env._('Sending Bank Branch: %(branch)s', branch=sending_bank_branch))
                if summary := rmspaces(line[159:179]):
                    note.append(env._('Note: %(note)s', note=summary))
                if edi_info := rmspaces(line[179:199]):
                    note.append(env._('EDI Information: %(info)s', info=edi_info))
            else:  # notice, term, fixed_deposit
                if deposit_date_str := rmspaces(line[71:77]):
                    note.append(env._('Initial Deposit Date: %(date)s', date=parsedate(deposit_date_str)))
                note.append(env._('Interest Rate: %(integer)s.%(decimal)s%', line[77:79], line[79:83]))
                if maturity_date_str := rmspaces(line[83:89]):
                    note.append(env._('Maturity Date: %(date)s', date=parsedate(maturity_date_str)))
                if period_str := rmspaces(line[89:95]):
                    note.append(env._('Period: %(date)s', date=parsedate(period_str)))
                if periodic_interest_str := rmspaces(line[95:102]):
                    note.append(env._('Periodic Interest: %(amount)s', amount=periodic_interest_str))
                if summary := rmspaces(line[171:191]):
                    note.append(env._('Note: %(note)s', note=summary))
            return note

        def parse_transaction_line(env, statement_type, line, deposit_type=None):
            if statement_type == 'transfer':
                if len(line) != 199:
                    raise UserError(env._('Incorrect transaction length: %(length)s', length=len(line)))
                exceed_amount = line[19: 29] == '0000000000'
                transaction = {
                    'date': parsedate(line[7:13]),
                    'amount': float(line[128:140]) if exceed_amount else float(line[19:29]),
                    'unique_import_id': line[1:7] + '/' + parsedate(line[7:13]),
                    'partner_name': rmspaces(line[49:97]),
                    'payment_ref': 'Transfer - ' + line[1:7],
                    'narration': plaintext2html('\n'.join(get_transfer_note(self.env, line, exceed_amount))),
                }
            else:
                if len(line) != 200:
                    raise UserError(env._('Incorrect transaction length: %(length)s', length=len(line)))
                payment_type = 'deposit' if line[21:22] == '1' else 'withdrawal'
                sign = -1 if payment_type == 'withdrawal' else 1
                transaction = {
                    'date': parsedate(line[9:15]),
                    'amount': sign * float(line[24: 36]),
                    'unique_import_id': line[1:9] + '/' + parsedate(line[9:15]),
                    'payment_ref': payment_type.capitalize() + ' - ' + line[1:9],
                    'narration': plaintext2html('\n'.join(get_deposit_withdrawal_note(self.env, line, deposit_type))),
                }
                if sender_name := rmspaces(line[81:129]):
                    transaction['partner_name'] = sender_name
            return transaction

        recordlist = record_data.split('\r\n')
        statement = {"transactions": []}
        statement_type = False
        acc_number = False
        deposit_type = False
        deposit_type_map = {
            '1': 'regular',
            '2': 'current',
            '4': 'savings',
            '5': 'notice',
            '6': 'term',
            '7': 'fixed_deposit',
        }

        for line in recordlist:
            if not line:
                pass
            elif line[0] == '1':  # Header
                statement_type, acc_number, result = parse_header(self.env, line)
                statement.update(result)
                if statement_type == 'deposit_withdrawal':
                    deposit_type = deposit_type_map.get(line[62:63])
                    if not deposit_type:
                        raise UserError(_('Unknown deposit type: %(type)s', type=line[62:63]))
            elif line[0] == '2':  # Detail
                if line[22:24] == '19':
                    continue  # Skip correction transactions
                transaction = parse_transaction_line(self.env, statement_type, line, deposit_type)
                statement['transactions'].append(transaction)
            elif line[0] == '8':  # Footer
                if statement_type == 'transfer':
                    continue
                if balance_end := rmspaces(line[115:129]):
                    statement['balance_end_real'] = float(balance_end)

        return 'JPY', acc_number, [statement]
