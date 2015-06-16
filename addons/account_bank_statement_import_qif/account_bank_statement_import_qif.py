# -*- coding: utf-8 -*-

import dateutil.parser
import StringIO

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def _get_hide_journal_field(self):
        return self.env.context and 'journal_id' in self.env.context or False

    journal_id = fields.Many2one('account.journal', string='Journal', help='Accounting journal related to the bank statement you\'re importing. It has be be manually chosen for statement formats which doesn\'t allow automatic journal detection (QIF for example).')
    hide_journal_field = fields.Boolean(string='Hide the journal field in the view', default=_get_hide_journal_field)

    def _find_additional_data(self, *args):
        """ As .QIF format does not allow us to detect the journal, we need to let the user choose it.
            We set it in context in the same way it's done when calling the import action from a journal.
        """
        if self.journal_id:
            self.env.context = dict(self.env.context, journal_id=self.journal_id.id)
        return super(AccountBankStatementImport, self)._find_additional_data(*args)

    def _check_qif(self, data_file):
        return data_file.strip().startswith('!Type:')

    def _parse_file(self, data_file):
        if not self._check_qif(data_file):
            return super(AccountBankStatementImport, self)._parse_file(data_file)

        try:
            file_data = ""
            for line in StringIO.StringIO(data_file).readlines():
                file_data += line
            if '\r' in file_data:
                data_list = file_data.split('\r')
            else:
                data_list = file_data.split('\n')
            header = data_list[0].strip()
            header = header.split(":")[1]
        except:
            raise UserError(_('Could not decipher the QIF file.'))
        transactions = []
        vals_line = {}
        total = 0
        if header == "Bank":
            vals_bank_statement = {}
            for line in data_list:
                line = line.strip()
                if not line:
                    continue
                if line[0] == 'D':  # date of transaction
                    vals_line['date'] = dateutil.parser.parse(line[1:], fuzzy=True).date()
                elif line[0] == 'T':  # Total amount
                    total += float(line[1:].replace(',', ''))
                    vals_line['amount'] = float(line[1:].replace(',', ''))
                elif line[0] == 'N':  # Check number
                    vals_line['ref'] = line[1:]
                elif line[0] == 'P':  # Payee
                    vals_line['name'] = 'name' in vals_line and line[1:] + ': ' + vals_line['name'] or line[1:]
                    # Since QIF doesn't provide account numbers, we'll have to find res.partner and res.partner.bank here
                    # (normal behavious is to provide 'account_number', which the generic module uses to find partner/bank)
                    partner_bank = self.env['res.partner.bank'].search([('owner_name', '=', line[1:])], limit=1)
                    if partner_bank:
                        vals_line['bank_account_id'] = partner_bank.id
                        vals_line['partner_id'] = partner_bank.partner_id.id
                elif line[0] == 'M':  # Memo
                    vals_line['name'] = 'name' in vals_line and vals_line['name'] + ': ' + line[1:] or line[1:]
                elif line[0] == '^':  # end of item
                    transactions.append(vals_line)
                    vals_line = {}
                elif line[0] == '\n':
                    transactions = []
                else:
                    pass
        else:
            raise UserError(_('This file is either not a bank statement or is not correctly formed.'))

        vals_bank_statement.update({
            'balance_end_real': total,
            'transactions': transactions
        })
        return None, None, [vals_bank_statement]
