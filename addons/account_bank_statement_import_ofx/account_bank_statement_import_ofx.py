# -*- coding: utf-8 -*-

import logging
import StringIO

from openerp import api, models, _
from openerp.exceptions import UserError
from ofxparse import OfxParser

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    def _check_ofx(self, file):
        try:
            ofx = OfxParser.parse(file)
        except:
            return False
        return ofx

    def _parse_file(self, data_file):
        ofx = self._check_ofx(StringIO.StringIO(data_file))
        if not ofx:
            return super(AccountBankStatementImport, self)._parse_file(data_file)

        transactions = []
        total_amt = 0.00
        try:
            for transaction in ofx.account.statement.transactions:
                # Since ofxparse doesn't provide account numbers, we'll have to find res.partner and res.partner.bank here
                # (normal behavious is to provide 'account_number', which the generic module uses to find partner/bank)
                bank_account_id = partner_id = False
                partner_bank = self.env['res.partner.bank'].search([('owner_name', '=', transaction.payee)], limit=1)
                if partner_bank:
                    bank_account_id = partner_bank.id
                    partner_id = partner_bank.partner_id.id
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

        vals_bank_statement = {
            'name': ofx.account.routing_number,
            'transactions': transactions,
            # WARNING: the provided ledger balance is not necessarily the ending balance of the statement
            # see https://github.com/odoo/odoo/issues/3003
            'balance_start': float(ofx.account.statement.balance) - total_amt,
            'balance_end_real': ofx.account.statement.balance,
        }
        return ofx.account.statement.currency, ofx.account.number, [vals_bank_statement]
