# -*- coding: utf-8 -*-

import dateutil.parser
import base64
from tempfile import TemporaryFile

from openerp.tools.translate import _
from openerp.osv import osv

from openerp.addons.account_bank_statement_import import account_bank_statement_import as ibs

ibs.add_file_type(('qif', 'QIF'))

class account_bank_statement_import(osv.TransientModel):
    _inherit = "account.bank.statement.import"

    def process_qif(self, cr, uid, data_file, journal_id=False, context=None):
        """ Import a file in the .QIF format"""
        try:
            fileobj = TemporaryFile('wb+')
            fileobj.write(base64.b64decode(data_file))
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
            raise osv.except_osv(_('Import Error!'), _('Please check QIF file format is proper or not.'))
        line_ids = []
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
                    if vals_line.get('date') and not vals_bank_statement.get('period_id'):
                        period_ids = self.pool.get('account.period').find(cr, uid, vals_line['date'], context=context)
                        vals_bank_statement.update({'period_id': period_ids and period_ids[0] or False})
                elif line[0] == 'T':  # Total amount
                    total += float(line[1:].replace(',', ''))
                    vals_line['amount'] = float(line[1:].replace(',', ''))
                elif line[0] == 'N':  # Check number
                    vals_line['ref'] = line[1:]
                elif line[0] == 'P':  # Payee
                    bank_account_id, partner_id = self._detect_partner(cr, uid, line[1:], identifying_field='owner_name', context=context)
                    vals_line['partner_id'] = partner_id
                    vals_line['bank_account_id'] = bank_account_id
                    vals_line['name'] = 'name' in vals_line and line[1:] + ': ' + vals_line['name'] or line[1:]
                elif line[0] == 'M':  # Memo
                    vals_line['name'] = 'name' in vals_line and vals_line['name'] + ': ' + line[1:] or line[1:]
                elif line[0] == '^':  # end of item
                    line_ids.append((0, 0, vals_line))
                    vals_line = {}
                elif line[0] == '\n':
                    line_ids = []
                else:
                    pass
        else:
            raise osv.except_osv(_('Error!'), _('Cannot support this Format !Type:%s.') % (header,))
        vals_bank_statement.update({'balance_end_real': total,
                                    'line_ids': line_ids,
                                    'journal_id': journal_id})
        return [vals_bank_statement]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
