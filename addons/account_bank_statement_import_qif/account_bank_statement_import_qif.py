# -*- coding: utf-8 -*-

import dateutil.parser
from tempfile import TemporaryFile

from openerp.tools.translate import _
from openerp.osv import osv, fields
from openerp.exceptions import UserError

class account_bank_statement_import(osv.TransientModel):
    _inherit = "account.bank.statement.import"

    _columns = {
        'journal_id': fields.many2one('account.journal', string='Journal', help='Accounting journal related to the bank statement you\'re importing. It has be be manually chosen for statement formats which doesn\'t allow automatic journal detection (QIF for example).'),
        'hide_journal_field': fields.boolean('Hide the journal field in the view'),
    }

    def _get_hide_journal_field(self, cr, uid, context=None):
        return context and 'journal_id' in context or False

    _defaults = {
        'hide_journal_field': _get_hide_journal_field,
    }

    def _get_journal(self, cr, uid, currency_id, bank_account_id, account_number, context=None):
        """ As .QIF format does not allow us to detect the journal, we need to let the user choose it. 
            We set it in context before to call super so it's the same as calling the widget from a journal """
        if context is None:
            context = {}
        if context.get('active_id'):
            record = self.browse(cr, uid, context.get('active_id'), context=context)
            if record.journal_id:
                context['journal_id'] = record.journal_id.id
        return super(account_bank_statement_import, self)._get_journal(cr, uid, currency_id, bank_account_id, account_number, context=context)

    def _check_qif(self, cr, uid, data_file, context=None):
        return data_file.strip().startswith('!Type:')

    def _parse_file(self, cr, uid, data_file=None, context=None):
        if not self._check_qif(cr, uid, data_file, context=context):
            return super(account_bank_statement_import, self)._parse_file(cr, uid, data_file, context=context)

        try:
            fileobj = TemporaryFile('wb+')
            fileobj.write(data_file)
            fileobj.seek(0)
            file_data = ""
            for line in fileobj.readlines():
                file_data += line
            fileobj.close()
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
                    ids = self.pool.get('res.partner.bank').search(cr, uid, [('owner_name', '=', line[1:])], context=context)
                    if ids:
                        vals_line['bank_account_id'] = bank_account_id = ids[0]
                        vals_line['partner_id'] = self.pool.get('res.partner.bank').browse(cr, uid, bank_account_id, context=context).partner_id.id
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

