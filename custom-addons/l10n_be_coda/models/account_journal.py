# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2012 Noviat nv/sa (www.noviat.be). All rights reserved.

import time
import re

from odoo import models, fields, tools, _, _lt
from odoo.exceptions import UserError


class safedict(dict):
    def __init__(self, *args, return_val=None, **kwargs):
        self.__return_val = return_val if return_val is not None else _('Wrong CODA code')
        super().__init__(*args, **kwargs)

    def __getitem__(self, k):
        return super().__getitem__(k) if k in self else self.__return_val


# Mappings for the structured communication formats
minimum = safedict({'1': _lt('minimum applicable'), '2': _lt('minimum not applicable')})
card_scheme = safedict({'1': _lt('Bancontact/Mister Cash'), '2': _lt('Maestro'), '3': _lt('Private'), '5': _lt('TINA'), '9': _lt('Other')})
transaction_type = safedict({'0': _lt('cumulative'), '1': _lt('withdrawal'), '2': _lt('cumulative on network'), '4': _lt('reversal of purchases'), '5': _lt('POS others'), '7': _lt('distribution sector'), '8': _lt('teledata'), '9': _lt('fuel')})
product_code = safedict({'00': _lt('unset'), '01': _lt('premium with lead substitute'), '02': _lt('europremium'), '03': _lt('diesel'), '04': _lt('LPG'), '06': _lt('premium plus 98 oct'), '07': _lt('regular unleaded'), '08': _lt('domestic fuel oil'), '09': _lt('lubricants'), '10': _lt('petrol'), '11': _lt('premium 99+'), '12': _lt('Avgas'), '16': _lt('other types')})
issuing_institution = safedict({'1': 'Mastercard', '2': 'Visa', '3': 'American Express', '4': 'Diners Club', '9': 'Other'})
type_direct_debit = safedict({'0': _lt('unspecified'), '1': _lt('recurrent'), '2': _lt('one-off'), '3': _lt('1-st (recurrent)'), '4': _lt('last (recurrent)')})
direct_debit_scheme = safedict({'0': _lt('unspecified'), '1': _lt('SEPA core'), '2': _lt('SEPA B2B')})
payment_reason = safedict({'0': _lt('paid'), '1': _lt('technical problem'), '2': _lt('reason not specified'), '3': _lt('debtor disagrees'), '4': _lt('debtor’s account problem')})
sepa_type = safedict({'0': _lt('paid'), '1': _lt('reject'), '2': _lt('return'), '3': _lt('refund'), '4': _lt('reversal'), '5': _lt('cancellation')})


sepa_transaction_type = safedict({
    0: _lt('Simple amount without detailed data'),
    1: _lt('Amount as totalised by the customer'),
    2: _lt('Amount as totalised by the bank'),
    3: _lt('Simple amount with detailed data'),
    5: _lt('Detail of Amount as totalised by the customer'),
    6: _lt('Detail of Amount as totalised by the bank'),
    7: _lt('Detail of Amount as totalised by the bank'),
    8: _lt('Detail of Simple amount with detailed data'),
    9: _lt('Detail of Amount as totalised by the bank'),
})

default_transaction_code = safedict({
    '40': _lt('Codes proper to each bank'), '41': _lt('Codes proper to each bank'), '42': _lt('Codes proper to each bank'), '43': _lt('Codes proper to each bank'), '44': _lt('Codes proper to each bank'), '45': _lt('Codes proper to each bank'), '46': _lt('Codes proper to each bank'), '47': _lt('Codes proper to each bank'), '48': _lt('Codes proper to each bank'),
    '49': _lt('Cancellation or correction'),
    '87': _lt('Reimbursement of costs'),
    '90': _lt('Codes proper to each bank'), '91': _lt('Codes proper to each bank'), '92': _lt('Codes proper to each bank'), '93': _lt('Codes proper to each bank'), '94': _lt('Codes proper to each bank'), '95': _lt('Codes proper to each bank'), '96': _lt('Codes proper to each bank'), '97': _lt('Codes proper to each bank'), '98': _lt('Codes proper to each bank'),
    '99': _lt('Cancellation or correction'),
})
transaction_code = safedict(**{
    'return_val': ('', {}),
    '01': (_lt('Domestic or local SEPA credit transfers'), {
        '01': _lt('Individual transfer order'),
        '02': _lt('Individual transfer order initiated by the bank'),
        '03': _lt('Standing order'),
        '05': _lt('Payment of wages, etc.'),
        '07': _lt('Collective transfer'),
        '13': _lt('Transfer from your account'),
        '17': _lt('Financial centralisation'),
        '37': _lt('Costs'),
        '39': _lt('Your issue circular cheque'),
        '50': _lt('Transfer in your favour'),
        '51': _lt('Transfer in your favour – initiated by the bank'),
        '52': _lt('Payment in your favour'),
        '54': _lt('Unexecutable transfer order'),
        '60': _lt('Non-presented circular cheque'),
        '62': _lt('Unpaid postal order'),
        '64': _lt('Transfer to your account'),
        '66': _lt('Financial centralization'),
    }),
    '02': (_lt('Instant SEPA credit transfer'), {
        '01': _lt('Individual transfer order'),
        '02': _lt('Individual transfer order initiated by the bank'),
        '03': _lt('Standing order'),
        '05': _lt('Payment of wages, etc.'),
        '07': _lt('Collective transfer'),
        '13': _lt('Transfer from your account'),
        '17': _lt('Financial centralisation'),
        '37': _lt('Costs'),
        '50': _lt('Transfer in your favour'),
        '51': _lt('Transfer in your favour – initiated by the bank'),
        '52': _lt('Payment in your favour'),
        '54': _lt('Unexecutable transfer order'),
        '64': _lt('Transfer to your account'),
        '66': _lt('Financial centralization'),
    }),
    '03': (_lt('Cheques'), {
        '01': _lt('Payment of your cheque'),
        '05': _lt('Payment of voucher'),
        '09': _lt('Unpaid voucher'),
        '11': _lt('Department store cheque'),
        '15': _lt('Your purchase bank cheque'),
        '17': _lt('Your certified cheque'),
        '37': _lt('Cheque-related costs'),
        '38': _lt('Provisionally unpaid'),
        '40': _lt('Codes proper to each bank'),
        '52': _lt('First credit of cheques, vouchers, luncheon vouchers, postal orders, credit under usual reserve'),
        '58': _lt('Remittance of cheques, vouchers, etc. credit after collection'),
        '60': _lt('Reversal of voucher'),
        '62': _lt('Reversal of cheque'),
        '63': _lt('Second credit of unpaid cheque'),
        '66': _lt('Remittance of cheque by your branch - credit under usual reserve'),
        '87': _lt('Reimbursement of cheque-related costs'),
    }),
    '04': (_lt('Cards'), {
        '01': _lt('Loading a GSM card'),
        '02': _lt('Payment by means of a payment card within the Eurozone'),
        '03': _lt('Settlement credit cards'),
        '04': _lt('Cash withdrawal from an ATM'),
        '05': _lt('Loading Proton'),
        '06': _lt('Payment with tank card'),
        '07': _lt('Payment by GSM'),
        '08': _lt('Payment by means of a payment card outside the Eurozone'),
        '09': _lt('Upload of prepaid card'),
        '10': _lt('Correction for prepaid card'),
        '37': _lt('Costs'),
        '50': _lt('Credit after a payment at a terminal'),
        '51': _lt('Unloading Proton'),
        '52': _lt('Loading GSM cards'),
        '53': _lt('Cash deposit at an ATM'),
        '54': _lt('Download of prepaid card'),
        '55': _lt('Income from payments by GSM'),
        '56': _lt('Correction for prepaid card'),
        '68': _lt('Credit after Proton payments'),
    }),
    '05': (_lt('Direct debit'), {
        '01': _lt('Payment'),
        '03': _lt('Unpaid debt'),
        '05': _lt('Reimbursement'),
        '37': _lt('Costs'),
        '50': _lt('Credit after collection'),
        '52': _lt('Credit under usual reserve'),
        '54': _lt('Reimbursement'),
        '56': _lt('Unexecutable reimbursement'),
        '58': _lt('Reversal'),
    }),
    '07': (_lt('Domestic commercial paper'), {
        '01': _lt('Payment commercial paper'),
        '05': _lt('Commercial paper claimed back'),
        '06': _lt('Extension of maturity date'),
        '07': _lt('Unpaid commercial paper'),
        '08': _lt('Payment in advance'),
        '09': _lt('Agio on supplier\'s bill'),
        '37': _lt('Costs related to commercial paper'),
        '39': _lt('Return of an irregular bill of exchange'),
        '50': _lt('Remittance of commercial paper - credit after collection'),
        '52': _lt('Remittance of commercial paper - credit under usual reserve'),
        '54': _lt('Remittance of commercial paper for discount'),
        '56': _lt('Remittance of supplier\'s bill with guarantee'),
        '58': _lt('Remittance of supplier\'s bill without guarantee'),
    }),
    '09': (_lt('Counter transactions'), {
        '01': _lt('Cash withdrawal'),
        '05': _lt('Purchase of foreign bank notes'),
        '07': _lt('Purchase of gold/pieces'),
        '09': _lt('Purchase of petrol coupons'),
        '13': _lt('Cash withdrawal by your branch or agents'),
        '17': _lt('Purchase of fiscal stamps'),
        '19': _lt('Difference in payment'),
        '25': _lt('Purchase of traveller’s cheque'),
        '37': _lt('Costs'),
        '50': _lt('Cash payment'),
        '52': _lt('Payment night safe'),
        '58': _lt('Payment by your branch/agents'),
        '60': _lt('Sale of foreign bank notes'),
        '62': _lt('Sale of gold/pieces under usual reserve'),
        '68': _lt('Difference in payment'),
        '70': _lt('Sale of traveller’s cheque'),
    }),
    '11': (_lt('Securities'), {
        '01': _lt('Purchase of securities'),
        '02': _lt('Tenders'),
        '03': _lt('Subscription to securities'),
        '04': _lt('Issues'),
        '05': _lt('Partial payment subscription'),
        '06': _lt('Share option plan – exercising an option'),
        '09': _lt('Settlement of securities'),
        '11': _lt('Payable coupons/repayable securities'),
        '13': _lt('Your repurchase of issue'),
        '15': _lt('Interim interest on subscription'),
        '17': _lt('Management fee'),
        '19': _lt('Regularisation costs'),
        '37': _lt('Costs'),
        '50': _lt('Sale of securities'),
        '51': _lt('Tender'),
        '52': _lt('Payment of coupons from a deposit or settlement of coupons delivered over the counter - credit under usual reserve'),
        '58': _lt('Repayable securities from a deposit or delivered at the counter - credit under usual reserve'),
        '62': _lt('Interim interest on subscription'),
        '64': _lt('Your issue'),
        '66': _lt('Retrocession of issue commission'),
        '68': _lt('Compensation for missing coupon'),
        '70': _lt('Settlement of securities'),
        '99': _lt('Cancellation or correction'),
    }),
    '13': (_lt('Credit'), {
        '01': _lt('Short-term loan'),
        '02': _lt('Long-term loan'),
        '05': _lt('Settlement of fixed advance'),
        '07': _lt('Your repayment instalment credits'),
        '11': _lt('Your repayment mortgage loan'),
        '13': _lt('Settlement of bank acceptances'),
        '15': _lt('Your repayment hire-purchase and similar claims'),
        '19': _lt('Documentary import credits'),
        '21': _lt('Other credit applications'),
        '37': _lt('Credit-related costs'),
        '50': _lt('Settlement of instalment credit'),
        '54': _lt('Fixed advance – capital and interest'),
        '55': _lt('Fixed advance – interest only'),
        '56': _lt('Subsidy'),
        '60': _lt('Settlement of mortgage loan'),
        '62': _lt('Term loan'),
        '68': _lt('Documentary export credits'),
        '70': _lt('Settlement of discount bank acceptance'),
    }),
    '30': (_lt('Various transactions'), {
        '01': _lt('Spot purchase of foreign exchange'),
        '03': _lt('Forward purchase of foreign exchange'),
        '05': _lt('Capital and/or interest term investment'),
        '33': _lt('Value (date) correction'),
        '37': _lt('Costs'),
        '39': _lt('Undefined transaction'),
        '50': _lt('Spot sale of foreign exchange'),
        '52': _lt('Forward sale of foreign exchange'),
        '54': _lt('Capital and/or interest term investment'),
        '55': _lt('Interest term investment'),
        '83': _lt('Value (date) correction'),
        '89': _lt('Undefined transaction'),
    }),
    '35': (_lt('Closing (periodical settlements for interest, costs,...)'), {
        '01': _lt('Closing'),
        '37': _lt('Costs'),
        '50': _lt('Closing'),
    }),
    '41': (_lt('International credit transfers - non-SEPA credit transfers'), {
        '01': _lt('Transfer'),
        '03': _lt('Standing order'),
        '05': _lt('Collective payments of wages'),
        '07': _lt('Collective transfers'),
        '13': _lt('Transfer from your account'),
        '17': _lt('Financial centralisation (debit)'),
        '37': _lt('Costs relating to outgoing foreign transfers and non-SEPA transfers'),
        '38': _lt('Costs relating to incoming foreign and non-SEPA transfers'),
        '50': _lt('Transfer'),
        '64': _lt('Transfer to your account'),
        '66': _lt('Financial centralisation (credit)'),
    }),
    '43': (_lt('Foreign cheques'), {
        '01': _lt('Payment of a foreign cheque'),
        '07': _lt('Unpaid foreign cheque'),
        '15': _lt('Purchase of an international bank cheque'),
        '37': _lt('Costs relating to payment of foreign cheques'),
        '52': _lt('Remittance of foreign cheque credit under usual reserve'),
        '58': _lt('Remittance of foreign cheque credit after collection'),
        '62': _lt('Reversal of cheques'),
    }),
    '47': (_lt('Foreign commercial paper'), {
        '01': _lt('Payment of foreign bill'),
        '05': _lt('Bill claimed back'),
        '06': _lt('Extension'),
        '07': _lt('Unpaid foreign bill'),
        '11': _lt('Payment documents abroad'),
        '13': _lt('Discount foreign supplier\'s bills'),
        '14': _lt('Warrant fallen due'),
        '37': _lt('Costs relating to the payment of a foreign bill'),
        '50': _lt('Remittance of foreign bill credit after collection'),
        '52': _lt('Remittance of foreign bill credit under usual reserve'),
        '54': _lt('Discount abroad'),
        '56': _lt('Remittance of guaranteed foreign supplier\'s bill'),
        '58': _lt('Idem without guarantee'),
        '60': _lt('Remittance of documents abroad - credit under usual reserve'),
        '62': _lt('Remittance of documents abroad - credit after collection'),
        '64': _lt('Warrant'),
    }),
    '80': (_lt('Separately charged costs and provisions'), {
        '02': _lt('Costs relating to electronic output'),
        '04': _lt('Costs for holding a documentary cash credit'),
        '06': _lt('Damage relating to bills and cheques'),
        '07': _lt('Insurance costs'),
        '08': _lt('Registering compensation for savings accounts'),
        '09': _lt('Postage'),
        '10': _lt('Purchase of Smartcard'),
        '11': _lt('Costs for the safe custody of correspondence'),
        '12': _lt('Costs for opening a bank guarantee'),
        '13': _lt('Renting of safes'),
        '14': _lt('Handling costs instalment credit'),
        '15': _lt('Night safe'),
        '16': _lt('Bank confirmation to revisor or accountant'),
        '17': _lt('Charge for safe custody'),
        '18': _lt('Trade information'),
        '19': _lt('Special charge for safe custody'),
        '20': _lt('Drawing up a certificate'),
        '21': _lt('Pay-packet charges'),
        '22': _lt('Management/custody'),
        '23': _lt('Research costs'),
        '24': _lt('Participation in and management of interest refund system'),
        '25': _lt('Renting of direct debit box'),
        '26': _lt('Travel insurance premium'),
        '27': _lt('Subscription fee'),
        '29': _lt('Information charges'),
        '31': _lt('Writ service fee'),
        '33': _lt('Miscellaneous fees and commissions'),
        '35': _lt('Costs'),
        '37': _lt('Access right to database'),
        '39': _lt('Surety fee'),
        '41': _lt('Research costs'),
        '43': _lt('Printing of forms'),
        '45': _lt('Documentary credit charges'),
        '47': _lt('Charging fees for transactions'),
    }),
})


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    coda_split_transactions = fields.Boolean(
        string="Split Transactions",
        help="Split collective payments for CODA files",
        default=True,
    )

    def _statement_import_check_bank_account(self, account_number):
        if self.bank_account_id.acc_type == 'iban' and self.bank_account_id.get_bban() == account_number:
            return True
        return super()._statement_import_check_bank_account(account_number)


    def _get_bank_statements_available_import_formats(self):
        rslt = super(AccountJournal, self)._get_bank_statements_available_import_formats()
        rslt.append('CODA')
        return rslt

    def _check_coda(self, coda_string):
        # Matches the first 24 characters of a CODA file, as defined by the febelfin specifications
        return re.match(r'0{5}\d{9}05[ D] +', coda_string) is not None

    def _parse_bank_statement_file(self, attachment):
        pattern = re.compile("[\u0020-\u1EFF\n\r]+")  # printable characters

        # Try different encodings for the file
        for encoding in ('utf_8', 'cp850', 'cp858', 'cp1140', 'cp1252', 'iso8859_15', 'utf_32', 'utf_16', 'windows-1252'):
            try:
                record_data = attachment.raw.decode(encoding)
            except UnicodeDecodeError:
                continue
            if pattern.fullmatch(record_data, re.MULTILINE):
                break  # We only have printable characters, stick with this one

        if not self._check_coda(record_data):
            return super()._parse_bank_statement_file(attachment)

        def rmspaces(s):
            return " ".join(s.split())

        def parsedate(s):
            if s == '999999':
                return _('No date')
            return "{day}/{month}/{year}".format(day=s[:2], month=s[2:4], year=s[4:])

        def parsehour(s):
            return "{hour}:{minute}".format(hour=s[:2], minute=s[2:])

        def parsefloat(s, precision):
            return str(float(rmspaces(s) or 0) / (10 ** precision))

        def parse_terminal(s):
            return _('Name: %(name)s, Town: %(city)s', name=rmspaces(s[:16]), city=rmspaces(s[16:]))

        def parse_operation(tr_type, family, operation, category):
            return "{tr_type}: {family} ({operation})".format(
                tr_type=sepa_transaction_type[tr_type],
                family=transaction_code[family][0],
                operation=transaction_code[family][1].get(operation, default_transaction_code.get(operation, _('undefined')))
            )

        def parse_structured_communication(co_type, communication):
            # pylint: disable=C0321,C0326
            note = []
            p_idx = 0 ; o_idx = 0
            if co_type == '100':  # RF Creditor Reference
                structured_com = rmspaces(communication[:25])
            elif co_type in ('101', '102'):  # Credit transfer or cash payment with structured format communication or with reconstituted structured format communication
                structured_com = '+++' + communication[:3] + '/' + communication[3:7] + '/' + communication[7:12] + '+++'
            elif co_type == '103':  # number (e.g. of the cheque, of the card, etc.)
                structured_com = rmspaces(communication[:12])
            elif co_type == '105':  # Original amount of the transaction
                structured_com = _('Original amount of the transaction')
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('Gross amount in the currency of the account') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('Gross amount in the original currency') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
                o_idx = p_idx; p_idx += 12; note.append(_('Detail') + ': ' + _('Rate') + ': ' + parsefloat(communication[o_idx:p_idx], 8))
                o_idx = p_idx; p_idx +=  3; note.append(_('Detail') + ': ' + _('Currency') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 12; note.append(_('Detail') + ': ' + _('Structured format communication') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  2; note.append(_('Detail') + ': ' + _('Country code of the principal') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('Equivalent in EUR') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
            elif co_type == '106':  # Method of calculation (VAT, withholding tax on income, commission, etc.)
                structured_com = _('Method of calculation (VAT, withholding tax on income, commission, etc.)')
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('equivalent in the currency of the account') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('amount on which % is calculated') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
                o_idx = p_idx; p_idx += 12; note.append(_('Detail') + ': ' + _('percent') + ': ' + parsefloat(communication[o_idx:p_idx], 8))
                o_idx = p_idx; p_idx +=  1; note.append(_('Detail') + ': ' + _('minimum') + ': ' + minimum[communication[o_idx:p_idx]])
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('equivalent in EUR') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
            elif co_type == '108':  # Closing
                structured_com = _('Closing')
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('equivalent in the currency of the account') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('interest rates, calculation basis') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 12; note.append(_('Detail') + ': ' + _('interest') + ': ' + parsefloat(communication[o_idx:p_idx], 8))
                o_idx = p_idx; p_idx += 12; note.append(_('Detail') + ': ' + _('period from %s to %s', parsedate(communication[o_idx:o_idx+6]), parsedate(communication[o_idx+6:o_idx+12])))
            elif co_type == '111':  # POS credit – Globalisation
                structured_com = _('POS credit – Globalisation')
                o_idx = p_idx; p_idx +=  1; note.append(_('Detail') + ': ' + _('card scheme') + ': ' + card_scheme[communication[o_idx:p_idx]])
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('POS number') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  3; note.append(_('Detail') + ': ' + _('period number') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('sequence number of first transaction') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('date of first transaction') + ': ' + parsedate(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('sequence number of last transaction') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('date of last transaction') + ': ' + parsedate(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  1; note.append(_('Detail') + ': ' + _('transaction type') + ': ' + transaction_type[communication[o_idx:p_idx]])
                o_idx = p_idx; p_idx += 26; note.append(_('Detail') + ': ' + _('identification of terminal') + ': ' + parse_terminal(communication[o_idx:p_idx]))
            elif co_type == '113':  # ATM/POS debit
                structured_com = _('ATM/POS debit')
                o_idx = p_idx; p_idx += 16; note.append(_('Detail') + ': ' + _('Masked PAN or card number') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  1; note.append(_('Detail') + ': ' + _('card scheme') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('terminal number') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('sequence number of transaction') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('date of transaction') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  4; note.append(_('Detail') + ': ' + _('hour of transaction') + ': ' + parsehour(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  1; note.append(_('Detail') + ': ' + _('transaction type') + ': ' + transaction_type[communication[o_idx:p_idx]])
                o_idx = p_idx; p_idx += 26; note.append(_('Detail') + ': ' + _('identification of terminal') + ': ' + parse_terminal(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('original amount') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
                o_idx = p_idx; p_idx += 12; note.append(_('Detail') + ': ' + _('rate') + ': ' + parsefloat(communication[o_idx:p_idx], 8))
                o_idx = p_idx; p_idx +=  3; note.append(_('Detail') + ': ' + _('currency') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  5; note.append(_('Detail') + ': ' + _('volume') + ': ' + parsefloat(communication[o_idx:p_idx], 2))
                o_idx = p_idx; p_idx +=  2; note.append(_('Detail') + ': ' + _('product code') + ': ' + product_code[communication[o_idx:p_idx]])
                o_idx = p_idx; p_idx +=  5; note.append(_('Detail') + ': ' + _('unit price') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
            elif co_type == '114':  # POS credit - individual transaction
                structured_com = _('POS credit - individual transaction')
                o_idx = p_idx; p_idx +=  1; note.append(_('Detail') + ': ' + _('card scheme') + ': ' + card_scheme[communication[o_idx:p_idx]])
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('POS number') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  3; note.append(_('Detail') + ': ' + _('period number') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('sequence number of transaction') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('date of transaction') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  4; note.append(_('Detail') + ': ' + _('hour of transaction') + ': ' + parsehour(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  1; note.append(_('Detail') + ': ' + _('transaction type') + ': ' + transaction_type[communication[o_idx:p_idx]])
                o_idx = p_idx; p_idx += 26; note.append(_('Detail') + ': ' + _('identification of terminal') + ': ' + parse_terminal(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 16; note.append(_('Detail') + ': ' + _('reference of transaction') + ': ' + rmspaces(communication[o_idx:p_idx]))
            elif co_type == '115':  # Terminal cash deposit
                structured_com = _('Terminal cash deposit')
                o_idx = p_idx; p_idx += 16; note.append(_('Detail') + ': ' + _('PAN or card number') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  1; note.append(_('Detail') + ': ' + _('card scheme') + ': ' + card_scheme[communication[o_idx:p_idx]])
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('terminal number') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('sequence number of transaction') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('payment day') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  4; note.append(_('Detail') + ': ' + _('hour of payment') + ': ' + parsehour(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('validation date') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('sequence number of validation') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('original amount (given by the customer)') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
                o_idx = p_idx; p_idx +=  1; note.append(_('Detail') + ': ' + _('conformity code or blank') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 26; note.append(_('Detail') + ': ' + _('identification of terminal') + ': ' + parse_terminal(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 12; note.append(_('Detail') + ': ' + _('message (structured of free)') + ': ' + rmspaces(communication[o_idx:p_idx]))
            elif co_type == '121':  # Commercial bills
                structured_com = _('Commercial bills')
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('amount of the bill') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('maturity date of the bill') + ': ' + parsedate(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('conventional maturity date') + ': ' + parsedate(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('date of issue of the bill') + ': ' + parsedate(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 11; note.append(_('Detail') + ': ' + _('company number') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  3; note.append(_('Detail') + ': ' + _('currency') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  3  # blanks
                o_idx = p_idx; p_idx += 13; note.append(_('Detail') + ': ' + _('number of the bill') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 12; note.append(_('Detail') + ': ' + _('exchange rate') + ': ' + parsefloat(communication[o_idx:p_idx], 8))
            elif co_type == '122':  # Bills - calculation of interest
                structured_com = _('Bills - calculation of interest')
                o_idx = p_idx; p_idx +=  4; note.append(_('Detail') + ': ' + _('number of days') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 12; note.append(_('Detail') + ': ' + _('interest rate') + ': ' + parsefloat(communication[o_idx:p_idx], 8))
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('basic amount of the calculation') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
                o_idx = p_idx; p_idx +=  1; note.append(_('Detail') + ': ' + _('minimum rate') + ': ' + minimum[communication[o_idx:p_idx]])
                o_idx = p_idx; p_idx += 13; note.append(_('Detail') + ': ' + _('number of the bill') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('maturity date of the bill') + ': ' + parsedate(communication[o_idx:p_idx]))
            elif co_type == '123':  # Fees and commissions
                structured_com = _('Fees and commissions')
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('starting date') + ': ' + parsedate(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('maturity date') + ': ' + parsedate(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('basic amount') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
                o_idx = p_idx; p_idx += 12; note.append(_('Detail') + ': ' + _('percentage') + ': ' + parsefloat(communication[o_idx:p_idx], 8))
                o_idx = p_idx; p_idx +=  4; note.append(_('Detail') + ': ' + _('term in days') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  1; note.append(_('Detail') + ': ' + _('minimum rate') + ': ' + minimum[communication[o_idx:p_idx]])
                o_idx = p_idx; p_idx += 13; note.append(_('Detail') + ': ' + _('guarantee number (no. allocated by the bank)') + ': ' + rmspaces(communication[o_idx:p_idx]))
            elif co_type == '124':  # Number of the credit card
                structured_com = _('Number of the credit card')
                o_idx = p_idx; p_idx += 20; note.append(_('Detail') + ': ' + _('Masked PAN or card number') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  1; note.append(_('Detail') + ': ' + _('issuing institution') + ': ' + issuing_institution[communication[o_idx:p_idx]])
                o_idx = p_idx; p_idx += 12; note.append(_('Detail') + ': ' + _('invoice number') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('identification number') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('date') + ': ' + parsedate(communication[o_idx:p_idx]))
            elif co_type == '125':  # Credit
                structured_com = _('Credit')
                o_idx = p_idx; p_idx += 12; note.append(_('Detail') + ': ' + _('account number of the credit') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('extension zone of account number of the credit') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('old balance of the credit') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('new balance of the credit') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('amount (equivalent in foreign currency)') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
                o_idx = p_idx; p_idx +=  3; note.append(_('Detail') + ': ' + _('currency') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('starting date') + ': ' + parsedate(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('end date') + ': ' + parsedate(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 12; note.append(_('Detail') + ': ' + _('nominal interest rate or rate of charge') + ': ' + parsefloat(communication[o_idx:p_idx], 8))
                o_idx = p_idx; p_idx += 13; note.append(_('Detail') + ': ' + _('reference of transaction on credit account') + ': ' + rmspaces(communication[o_idx:p_idx]))
            elif co_type == '126':  # Term Investments
                structured_com = _('Term Investments')
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('deposit number') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('deposit amount') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('equivalent in the currency of the account') + ': ' + parsefloat(communication[o_idx:p_idx], 3))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('starting date') + ': ' + parsedate(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('end date') + ': ' + parsedate(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 12; note.append(_('Detail') + ': ' + _('interest rate') + ': ' + parsefloat(communication[o_idx:p_idx], 8))
                o_idx = p_idx; p_idx += 15; note.append(_('Detail') + ': ' + _('amount of interest') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  3; note.append(_('Detail') + ': ' + _('currency') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 12; note.append(_('Detail') + ': ' + _('rate') + ': ' + parsefloat(communication[o_idx:p_idx], 8))
            elif co_type == '127':  # SEPA
                structured_com = _('SEPA Direct Debit')
                o_idx = p_idx; p_idx +=  6; note.append(_('Detail') + ': ' + _('Settlement Date') + ': ' + parsedate(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  1; note.append(_('Detail') + ': ' + _('Type Direct Debit') + ': ' + type_direct_debit[communication[o_idx:p_idx]])
                o_idx = p_idx; p_idx +=  1; note.append(_('Detail') + ': ' + _('Direct Debit scheme') + ': ' + direct_debit_scheme[communication[o_idx:p_idx]])
                o_idx = p_idx; p_idx +=  1; note.append(_('Detail') + ': ' + _('Paid or reason for refused payment') + ': ' + payment_reason[communication[o_idx:p_idx]])
                o_idx = p_idx; p_idx += 35; note.append(_('Detail') + ': ' + _('Creditor’s identification code') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 35; note.append(_('Detail') + ': ' + _('Mandate reference') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx += 62; note.append(_('Detail') + ': ' + _('Communicaton') + ': ' + rmspaces(communication[o_idx:p_idx]))
                o_idx = p_idx; p_idx +=  1; note.append(_('Detail') + ': ' + _('Type of R transaction') + ': ' + sepa_type[communication[o_idx:p_idx]])
                o_idx = p_idx; p_idx +=  4; note.append(_('Detail') + ': ' + _('Reason') + ': ' + rmspaces(communication[o_idx:p_idx]))
            else:
                structured_com = _('Type of structured communication not supported: ') + co_type
                note.append(communication)
            return structured_com, note

        recordlist = record_data.split(u'\n')
        statements = []
        globalisation_comm = {}
        for line in recordlist:
            if not line:
                pass
            elif line[0] == '0':
                #Begin of a new Bank statement
                statement = {}
                statements.append(statement)
                statement['version'] = line[127]
                if statement['version'] not in ['1', '2']:
                    raise UserError(_('Error') + ' R001: ' + _('CODA V%s statements are not supported, please contact your bank', statement['version']))
                statement['globalisation_stack'] = []
                statement['lines'] = []
                statement['date'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[5:11]), '%d%m%y'))
                statement['separateApplication'] = rmspaces(line[83:88])
            elif line[0] == '1':
                #Statement details
                if statement['version'] == '1':
                    statement['acc_number'] = rmspaces(line[5:17])
                    statement['currency'] = rmspaces(line[18:21])
                elif statement['version'] == '2':
                    if line[1] == '0':  # Belgian bank account BBAN structure
                        statement['acc_number'] = rmspaces(line[5:17])
                        # '11' and '14' stand respecively for characters 'B' and 'E', it's a constant for Belgium, that we need to append to the account number before computing the check digits
                        statement['acc_number'] = 'BE%02d' % (98 - int(statement['acc_number'] + '111400') % 97) + statement['acc_number']
                        statement['currency'] = rmspaces(line[18:21])
                    elif line[1] == '1':  # foreign bank account BBAN structure
                        raise UserError(_('Error') + ' R1001: ' + _('Foreign bank accounts with BBAN structure are not supported '))
                    elif line[1] == '2':    # Belgian bank account IBAN structure
                        statement['acc_number'] = rmspaces(line[5:21])
                        statement['currency'] = rmspaces(line[39:42])
                    elif line[1] == '3':    # foreign bank account IBAN structure
                        statement['acc_number'] = rmspaces(line[5:39])
                        statement['currency'] = rmspaces(line[39:42])
                    else:  # Something else, not supported
                        raise UserError(_('Error') + ' R1003: ' + _('Unsupported bank account structure '))
                statement['description'] = rmspaces(line[90:125])
                statement['balance_start'] = float(rmspaces(line[43:58])) / 1000
                if line[42] == '1':  # 1 = Debit, the starting balance is negative
                    statement['balance_start'] = - statement['balance_start']
                statement['balance_start_date'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[58:64]), '%d%m%y')) if rmspaces(line[58:64]) != '000000' else statement['date']
                statement['accountHolder'] = rmspaces(line[64:90])
                statement['paperSeqNumber'] = rmspaces(line[2:5])
                statement['codaSeqNumber'] = rmspaces(line[125:128])
            elif line[0] == '2':
                if line[1] == '1':
                    #New statement line
                    statementLine = {}
                    statementLine['ref'] = rmspaces(line[2:10])
                    statementLine['ref_move'] = rmspaces(line[2:6])
                    statementLine['ref_move_detail'] = rmspaces(line[6:10])
                    statementLine['sequence'] = len(statement['lines']) + 1
                    statementLine['transactionRef'] = rmspaces(line[10:31])
                    statementLine['debit'] = line[31]  # 0 = Credit, 1 = Debit
                    statementLine['amount'] = float(rmspaces(line[32:47])) / 1000
                    if statementLine['debit'] == '1':
                        statementLine['amount'] = - statementLine['amount']
                    statementLine['transactionDate'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[47:53]), '%d%m%y')) if rmspaces(line[47:53]) != '000000' else statement['date']
                    statementLine['transaction_type'] = int(rmspaces(line[53:54]))
                    statementLine['transaction_family'] = rmspaces(line[54:56])
                    statementLine['transaction_code'] = rmspaces(line[56:58])
                    statementLine['transaction_category'] = rmspaces(line[58:61])
                    if line[61] == '1':
                        #Structured communication
                        statementLine['communication_struct'] = True
                        statementLine['communication_type'] = line[62:65]
                        statementLine['communication'] = line[65:115]
                    else:
                        #Non-structured communication
                        statementLine['communication_struct'] = False
                        statementLine['communication'] = rmspaces(line[62:115])
                    statementLine['entryDate'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[115:121]), '%d%m%y'))
                    statementLine['type'] = 'normal'
                    statementLine['globalisation'] = int(line[124])
                    if statementLine['globalisation'] > 0:
                        if statementLine['ref_move'] in statement['globalisation_stack']:
                            statement['globalisation_stack'].remove(statementLine['ref_move'])
                        else:
                            statementLine['type'] = 'globalisation'
                            statement['globalisation_stack'].append(statementLine['ref_move'])
                            globalisation_comm[statementLine['ref_move']] = statementLine['communication']
                    if not statementLine.get('communication'):
                        statementLine['communication'] = globalisation_comm.get(statementLine['ref_move'], '')
                    statement['lines'].append(statementLine)
                elif line[1] == '2':
                    if statement['lines'][-1]['ref'][0:4] != line[2:6]:
                        raise UserError(_('Error') + 'R2004: ' + _('CODA parsing error on movement data record 2.2, seq nr %s! Please report this issue via your Odoo support channel.', line[2:10]))
                    statement['lines'][-1]['communication'] += line[10:63]
                    statement['lines'][-1]['payment_reference'] = rmspaces(line[63:98])
                    statement['lines'][-1]['counterparty_bic'] = rmspaces(line[98:109])
                    # TODO 113, 114-117, 118-121, 122-125
                elif line[1] == '3':
                    if statement['lines'][-1]['ref'][0:4] != line[2:6]:
                        raise UserError(_('Error') + 'R2005: ' + _('CODA parsing error on movement data record 2.3, seq nr %s! Please report this issue via your Odoo support channel.', line[2:10]))
                    if statement['version'] == '1':
                        statement['lines'][-1]['counterpartyNumber'] = rmspaces(line[10:22])
                        statement['lines'][-1]['counterpartyName'] = rmspaces(line[47:73])
                        statement['lines'][-1]['counterpartyAddress'] = rmspaces(line[73:125])
                        statement['lines'][-1]['counterpartyCurrency'] = ''
                    else:
                        if line[22] == ' ':
                            statement['lines'][-1]['counterpartyNumber'] = rmspaces(line[10:22])
                            statement['lines'][-1]['counterpartyCurrency'] = rmspaces(line[23:26])
                        else:
                            statement['lines'][-1]['counterpartyNumber'] = rmspaces(line[10:44])
                            statement['lines'][-1]['counterpartyCurrency'] = rmspaces(line[44:47])
                        statement['lines'][-1]['counterpartyName'] = rmspaces(line[47:82])
                        statement['lines'][-1]['communication'] += line[82:125]
                else:
                    # movement data record 2.x (x != 1,2,3)
                    raise UserError(_('Error') + 'R2006: ' + _('\nMovement data records of type 2.%s are not supported ', line[1]))
            elif line[0] == '3':
                if line[1] == '1':
                    infoLine = {}
                    infoLine['entryDate'] = statement['lines'][-1]['entryDate']
                    infoLine['type'] = 'information'
                    infoLine['sequence'] = len(statement['lines']) + 1
                    infoLine['ref'] = rmspaces(line[2:10])
                    infoLine['ref_move'] = rmspaces(line[2:6])
                    infoLine['ref_move_detail'] = rmspaces(line[6:10])
                    infoLine['transactionRef'] = rmspaces(line[10:31])
                    infoLine['transaction_family'] = rmspaces(line[32:34])
                    infoLine['transaction_code'] = rmspaces(line[34:36])
                    infoLine['transaction_category'] = rmspaces(line[36:39])
                    if line[39] == '1':
                        #Structured communication
                        infoLine['communication_struct'] = True
                        infoLine['communication_type'] = line[40:43]
                        infoLine['communication'] = line[43:113]
                    else:
                        #Non-structured communication
                        infoLine['communication_struct'] = False
                        infoLine['communication'] = line[40:113]
                    statement['lines'].append(infoLine)
                elif line[1] == '2':
                    if infoLine['ref'] != rmspaces(line[2:10]):
                        raise UserError(_('Error') + 'R3004: ' + _('CODA parsing error on information data record 3.2, seq nr %s! Please report this issue via your Odoo support channel.', line[2:10]))
                    statement['lines'][-1]['communication'] += rmspaces(line[10:115])
                elif line[1] == '3':
                    if infoLine['ref'] != rmspaces(line[2:10]):
                        raise UserError(_('Error') + 'R3005: ' + _('CODA parsing error on information data record 3.3, seq nr %s! Please report this issue via your Odoo support channel.', line[2:10]))
                    statement['lines'][-1]['communication'] += rmspaces(line[10:100])
            elif line[0] == '4':
                comm_line = {}
                comm_line['type'] = 'communication'
                comm_line['sequence'] = len(statement['lines']) + 1
                comm_line['ref'] = rmspaces(line[2:10])
                comm_line['ref_move'] = rmspaces(line[2:6])
                comm_line['ref_move_detail'] = rmspaces(line[6:10])
                comm_line['communication'] = line[32:112]
                statement['lines'].append(comm_line)
            elif line[0] == '8':
                # new balance record
                statement['debit'] = line[41]
                statement['paperSeqNumber'] = rmspaces(line[1:4])
                statement['balance_end_real'] = float(rmspaces(line[42:57])) / 1000
                statement['balance_end_realDate'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[57:63]), '%d%m%y'))
                if statement['debit'] == '1':    # 1=Debit
                    statement['balance_end_real'] = - statement['balance_end_real']
            elif line[0] == '9':
                statement['balanceMin'] = float(rmspaces(line[22:37])) / 1000
                statement['balancePlus'] = float(rmspaces(line[37:52])) / 1000
                if not statement.get('balance_end_real'):
                    statement['balance_end_real'] = statement['balance_start'] + statement['balancePlus'] - statement['balanceMin']
        ret_statements = []
        for statement in statements:
            statement['coda_note'] = ''
            statement_line = []
            statement_data = {
                'name': int(statement['paperSeqNumber']),
                'date': statement['date'],
                'balance_start': statement['balance_start'],
                'balance_end_real': statement['balance_end_real'],
            }
            temp_data = {}
            for line in statement['lines']:
                to_add = statement_line and statement_line[-1]['ref'][:4] == line.get('ref_move') and statement_line[-1] or temp_data
                if line['type'] == 'information':
                    if line['communication_struct']:
                        to_add['narration'] = "\n".join([to_add.get('narration', ''), 'Communication: '] + parse_structured_communication(line['communication_type'], line['communication'])[1])
                    else:
                        to_add['narration'] = "\n".join([to_add.get('narration', ''), line['communication']])
                elif line['type'] == 'communication':
                    statement['coda_note'] = "%s[%s] %s\n" % (statement['coda_note'], str(line['ref']), line['communication'])
                elif line['type'] == 'normal'\
                        or (line['type'] == 'globalisation' and line['ref_move'] in statement['globalisation_stack'] and line['transaction_type'] in [1, 2]):
                    note = []
                    if line.get('counterpartyName'):
                        note.append(_('Counter Party') + ': ' + line['counterpartyName'])
                    else:
                        line['counterpartyName'] = False
                    if line.get('counterpartyNumber'):
                        try:
                            if int(line['counterpartyNumber']) == 0:
                                line['counterpartyNumber'] = False
                        except ValueError:
                            pass
                        if (
                            line.get('transaction_family', '') in ('01', '02', '41')  # Credit transfer
                            and line.get('transaction_code', '') == '07'  # Collective transfer
                        ):
                            line['counterpartyNumber'] = False
                        if line['counterpartyNumber']:
                            note.append(_('Counter Party Account') + ': ' + line['counterpartyNumber'])
                    else:
                        line['counterpartyNumber'] = False

                    if line.get('counterpartyAddress'):
                        note.append(_('Counter Party Address') + ': ' + line['counterpartyAddress'])
                    structured_com = False
                    if line['communication_struct']:
                        structured_com, extend_notes = parse_structured_communication(line['communication_type'], line['communication'])
                        note.extend(extend_notes)
                    elif line.get('communication'):
                        note.append(_('Communication') + ': ' + rmspaces(line['communication']))
                    if not self.coda_split_transactions and statement_line and line['ref_move'] == statement_line[-1]['ref'][:4]:
                        to_add['amount'] = to_add.get('amount', 0) + line['amount']
                        to_add['narration'] = to_add.get('narration', '') + "\n" + "\n".join(note)
                    else:
                        line_data = {
                            'payment_ref': structured_com or line.get('communication', '') or '/',
                            'narration': "\n".join(note),
                            'transaction_type': parse_operation(line['transaction_type'], line['transaction_family'], line['transaction_code'], line['transaction_category']),
                            'date': line['entryDate'],
                            'amount': line['amount'],
                            'account_number': line.get('counterpartyNumber', None),
                            'partner_name': line['counterpartyName'],
                            'ref': self.coda_split_transactions and line['ref'] or line['ref_move'],
                            'sequence': line['sequence'],
                            'unique_import_id': str(statement['codaSeqNumber']) + '-' + str(statement['date']) + '-' + str(line['ref']),
                        }
                        if temp_data.get('narration'):
                            line_data['narration'] = temp_data.pop('narration') + '\n' + line_data['narration']
                        if temp_data.get('amount'):
                            line_data['amount'] += temp_data.pop('amount')
                        statement_line.append(line_data)
            if statement['coda_note'] != '':
                statement_data.update({'coda_note': _('Communication: ') + '\n' + statement['coda_note']})
            statement_data.update({'transactions': statement_line})
            ret_statements.append(statement_data)

        # Order the transactions according the newly created statements to ensure valid balances.
        line_sequence = 1
        for statement_vals in reversed(ret_statements):
            for statement_line_vals in reversed(statement_vals.get('transactions', [])):
                statement_line_vals['sequence'] = line_sequence
                line_sequence += 1

        currency_code = statement['currency']
        acc_number = statements[0] and statements[0]['acc_number'] or False
        return currency_code, acc_number, ret_statements
