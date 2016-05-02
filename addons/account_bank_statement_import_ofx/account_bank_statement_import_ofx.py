# -*- coding: utf-8 -*-

import logging
import StringIO

from openerp.osv import osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from ofxparse import OfxParser as ofxparser
except ImportError:
    _logger.warn("ofxparse not found, OFX parsing disabled.")
    ofxparser = None

class account_bank_statement_import(osv.TransientModel):
    _inherit = 'account.bank.statement.import'

    def _check_ofx(self, cr, uid, file, context=None):
        if ofxparser is None:
            return False
        try:
            ofx = ofxparser.parse(file)
        except:
            return False
        return ofx

    def _parse_file(self, cr, uid, data_file, context=None):
        ofx = self._check_ofx(cr, uid, StringIO.StringIO(data_file), context=context)
        if not ofx:
            return super(account_bank_statement_import, self)._parse_file(cr, uid, data_file, context=context)

        vals_bank_statement = []
        account_lst = set()
        currency_lst = set()
        for account in ofx.accounts:
            account_lst.add(account.number)
            currency_lst.add(account.statement.currency)
            transactions = []
            total_amt = 0.00
            try:
                for transaction in account.statement.transactions:
                    # Since ofxparse doesn't provide account numbers, we'll have to find res.partner and res.partner.bank here
                    # (normal behavious is to provide 'account_number', which the generic module uses to find partner/bank)
                    bank_account_id = partner_id = False
                    ids = self.pool.get('res.partner.bank').search(cr, uid, [('owner_name', '=', transaction.payee)], context=context)
                    if ids:
                        bank_account_id = bank_account_id = ids[0]
                        partner_id = self.pool.get('res.partner.bank').browse(cr, uid, bank_account_id, context=context).partner_id.id
                    vals_line = {
                        'date': transaction.date,
                        'name': transaction.payee + (transaction.memo and ': ' + transaction.memo or ''),
                        'ref': transaction.id,
                        'amount': transaction.amount,
                        'unique_import_id': transaction.id,
                        'bank_account_id': bank_account_id,
                        'partner_id': partner_id,
                    }
                    total_amt += float(transaction.amount)
                    transactions.append(vals_line)
            except Exception, e:
                raise UserError(_("The following problem occurred during import. The file might not be valid.\n\n %s" % e.message))

            vals_bank_statement.append({
                'name': account.routing_number,
                'transactions': transactions,
                # WARNING: the provided ledger balance is not necessarily the ending balance of the statement
                # see https://github.com/odoo/odoo/issues/3003
                'balance_start': float(account.statement.balance) - total_amt,
                'balance_end_real': account.statement.balance,
            })

        if account_lst and len(account_lst) == 1:
            account_lst = account_lst.pop()
            currency_lst = currency_lst.pop()
        else:
            account_lst = None
            currency_lst = None

        return currency_lst, account_lst, vals_bank_statement
