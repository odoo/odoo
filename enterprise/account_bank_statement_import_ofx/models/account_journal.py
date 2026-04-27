
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import io
import logging
import re
import unicodedata
from xml.etree import ElementTree

try:
    from ofxparse import OfxParser
    OfxParserClass = OfxParser
except ImportError:
    logging.getLogger(__name__).warning("The ofxparse python library is not installed, ofx import will not work.")
    OfxParser = None
    OfxParserClass = object

from odoo import models, _
from odoo.exceptions import UserError


class PatchedOfxParser(OfxParserClass):
    """ This class monkey-patches the ofxparse library in order to fix the following known bug: ',' is a valid
        decimal separator for amounts, as we can encounter in ofx files made by european banks.
    """

    @classmethod
    def decimal_separator_cleanup(cls, tag):
        if hasattr(tag, "contents"):
            tag.string = tag.contents[0].replace(',', '.')

    @classmethod
    def parseStatement(cls, stmt_ofx):
        ledger_bal_tag = stmt_ofx.find('ledgerbal')
        if hasattr(ledger_bal_tag, "contents"):
            balamt_tag = ledger_bal_tag.find('balamt')
            cls.decimal_separator_cleanup(balamt_tag)
        avail_bal_tag = stmt_ofx.find('availbal')
        if hasattr(avail_bal_tag, "contents"):
            balamt_tag = avail_bal_tag.find('balamt')
            cls.decimal_separator_cleanup(balamt_tag)
        return super().parseStatement(stmt_ofx)

    @classmethod
    def parseTransaction(cls, txn_ofx):
        amt_tag = txn_ofx.find('trnamt')
        cls.decimal_separator_cleanup(amt_tag)
        return super().parseTransaction(txn_ofx)

    @classmethod
    def parseInvestmentPosition(cls, ofx):
        tag = ofx.find('units')
        cls.decimal_separator_cleanup(tag)
        tag = ofx.find('unitprice')
        cls.decimal_separator_cleanup(tag)
        return super().parseInvestmentPosition(ofx)

    @classmethod
    def parseInvestmentTransaction(cls, ofx):
        tag = ofx.find('units')
        cls.decimal_separator_cleanup(tag)
        tag = ofx.find('unitprice')
        cls.decimal_separator_cleanup(tag)
        return super().parseInvestmentTransaction(ofx)

    @classmethod
    def parseOfxDateTime(cls, ofxDateTime):
        res = re.search(r"^[0-9]*\.([0-9]{0,5})", ofxDateTime)
        if res:
            msec = datetime.timedelta(seconds=float("0." + res.group(1)))
        else:
            msec = datetime.timedelta(seconds=0)

        # Some banks seem to return some OFX dates as YYYY-MM-DD; so we remove
        # the '-' characters to support them as well
        ofxDateTime = ofxDateTime.replace('-', '')

        try:
            local_date = datetime.datetime.strptime(
                ofxDateTime[:14], '%Y%m%d%H%M%S'
            )
            return local_date + msec
        except Exception:
            if not ofxDateTime or ofxDateTime[:8] == "00000000":
                return None

            return datetime.datetime.strptime(
                ofxDateTime[:8], '%Y%m%d') + msec


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _get_bank_statements_available_import_formats(self):
        rslt = super(AccountJournal, self)._get_bank_statements_available_import_formats()
        rslt.append('OFX')
        return rslt


    def _check_ofx(self, attachment):
        if (attachment.raw or b'').startswith(b"OFXHEADER"):
            #v1 OFX
            return True
        try:
            #v2 OFX
            return b"<ofx>" in (attachment.raw or b'').lower()
        except ElementTree.ParseError:
            return False

    def _fill_transaction_vals_line_ofx(self, transaction, length_transactions, partner_bank):
        return {
            'date': transaction.date,
            'payment_ref': transaction.payee + (transaction.memo and ': ' + transaction.memo or ''),
            'ref': transaction.id,
            'amount': float(transaction.amount),
            'unique_import_id': transaction.id,
            'account_number': partner_bank.acc_number,
            'partner_id': partner_bank.partner_id.id,
            'sequence': length_transactions + 1,
        }

    def _parse_bank_statement_file(self, attachment):
        if not self._check_ofx(attachment):
            return super()._parse_bank_statement_file(attachment)
        if OfxParser is None:
            raise UserError(_("The library 'ofxparse' is missing, OFX import cannot proceed."))

        try:
            ofx = PatchedOfxParser.parse(io.BytesIO(attachment.raw))
        except UnicodeDecodeError:
            # Replacing utf-8 chars with ascii equivalent
            encoding = re.findall(b'encoding="(.*?)"', attachment.raw)
            encoding = encoding[0] if len(encoding) > 1 else 'utf-8'
            try:
                attachment = unicodedata.normalize('NFKD', attachment.raw.decode(encoding)).encode('ascii', 'ignore')
                ofx = PatchedOfxParser.parse(io.BytesIO(attachment))
            except UnicodeDecodeError:
                raise UserError(_("There was an issue decoding the file. Please check the file encoding."))
        vals_bank_statement = []
        account_lst = set()
        currency_lst = set()
        # Since ofxparse doesn't provide account numbers, we'll have to find res.partner and res.partner.bank here
        # (normal behaviour is to provide 'account_number', which the generic module uses to find partner/bank)
        transaction_payees = [
            transaction.payee
            for account in ofx.accounts
            for transaction in account.statement.transactions
        ]
        partner_banks_dict = {
            partner_bank.partner_id.name: partner_bank
            for partner_bank in self.env['res.partner.bank'].search([
                ('partner_id.name', 'in', transaction_payees)
            ])
        }
        for account in ofx.accounts:
            account_lst.add(account.number)
            currency_lst.add(account.statement.currency)
            transactions = []
            total_amt = 0.00
            for transaction in account.statement.transactions:
                partner_bank = partner_banks_dict.get(transaction.payee, self.env['res.partner.bank'])
                vals_line = self._fill_transaction_vals_line_ofx(transaction, len(transactions), partner_bank)
                total_amt += float(transaction.amount)
                transactions.append(vals_line)

            vals_bank_statement.append({
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
