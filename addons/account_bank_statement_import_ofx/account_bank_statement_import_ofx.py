# -*- coding: utf-8 -*-

import logging
import os

from openerp.osv import osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

try:
    from ofxparse import OfxParser as ofxparser
except ImportError:
    _logger.error("OFX parser unavailable because the `ofxparse` Python library cannot be found."
                    "It can be downloaded and installed from `https://pypi.python.org/pypi/ofxparse`.")
    ofxparser = None

class account_bank_statement_import(osv.TransientModel):
    _inherit = 'account.bank.statement.import'

    def _check_ofx(self, cr, uid, file, context=None):
        if ofxparser is None:
            return False
        try:
            ofxparser.parse(file)
        except:
            return False
        return True

    def _parse_file(self, cr, uid, data_file=None, context=None):
        try:
            tempfile = open("temp.ofx", "w+")
            tempfile.write(data_file)
            tempfile.read()
            pathname = os.path.dirname('temp.ofx')
            path = os.path.join(os.path.abspath(pathname), 'temp.ofx')
        except:
            raise osv.except_osv(_('Import Error!'), _('File handling error.'))
        if not self._check_ofx(cr, uid, file(path), context=context):
            return super(account_bank_statement_import, self)._parse_file(cr, uid, data_file, context=context)
        try:
            ofx = ofxparser.parse(file(path))
        except:
            os.remove(path)
            raise osv.except_osv(_('Import Error!'), _('Could not decipher the OFX file.'))

        transactions = []
        total_amt = 0.00
        try:
            for transaction in ofx.account.statement.transactions:
                vals_line = {
                    'date': transaction.date,
                    'name': transaction.payee + (transaction.memo and ': ' + transaction.memo or ''),
                    'ref': transaction.id,
                    'amount': transaction.amount,
                    'unique_import_id': transaction.id,
                    'counterparty_identification_string': transaction.payee,
                }
                total_amt += float(transaction.amount)
                transactions.append(vals_line)
        except Exception, e:
            os.remove(path)
            raise osv.except_osv(_('Error!'), _("The following problem occurred during import. The file might not be valid.\n\n %s" % e.message))

        vals_bank_statement = {
            'name': ofx.account.routing_number,
            'transactions': transactions,
            'balance_start': ofx.account.statement.balance,
            'balance_end_real': float(ofx.account.statement.balance) + total_amt,
        }
        os.remove(path)
        return ofx.account.statement.currency, ofx.account.number, 'owner_name', [vals_bank_statement]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
