# -*- coding: utf-8 -*-

import dateutil.parser
from tempfile import TemporaryFile

from openerp.tools.translate import _
from openerp.osv import osv

class account_bank_statement_import(osv.TransientModel):
    _inherit = "account.bank.statement.import"

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
            raise osv.except_osv(_('Import Error!'), _('Could not decipher the QIF file.'))
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
                    vals_line['counterparty_identification_string'] = line[1:]
                    vals_line['name'] = 'name' in vals_line and line[1:] + ': ' + vals_line['name'] or line[1:]
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
            raise osv.except_osv(_('Error!'), _('This file is either not a bank statement or is not correctly formed.'))
        
        vals_bank_statement.update({
            'balance_end_real': total,
            'transactions': transactions
        })
        return None, None, 'owner_name', [vals_bank_statement]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
