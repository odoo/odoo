# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2012 Noviat nv/sa (www.noviat.be). All rights reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import base64
from osv import fields, osv
from tools.translate import _
import time
import tools
import logging
_logger = logging.getLogger(__name__)


class account_coda_import(osv.osv_memory):
    _name = 'account.coda.import'
    _description = 'Import CODA File'
    _columns = {
        'coda_data': fields.binary('CODA File', required=True),
        'coda_fname': fields.char('CODA Filename', size=128, required=True),
        'note': fields.text('Log'),
    }
    _defaults = {
        'coda_fname': lambda *a: '',
    }

    def coda_parsing(self, cr, uid, ids, context=None, batch=False, codafile=None, codafilename=None):
        if context is None:
            context = {}
        if batch:
            codafile = str(codafile)
            codafilename = codafilename
        else:
            data = self.browse(cr, uid, ids)[0]
            try:
                codafile = data.coda_data
                codafilename = data.coda_fname
            except:
                raise osv.except_osv(_('Error'), _('Wizard in incorrect state. Please hit the Cancel button'))
                return {}
        recordlist = unicode(base64.decodestring(codafile), 'windows-1252', 'strict').split('\n')
        statements = []
        for line in recordlist:
            if not line:
                pass
            elif line[0] == '0':
                #Begin of a new Bank statement
                statement = {}
                statements.append(statement)
                statement['version'] = line[127]
                if statement['version'] not in ['1', '2']:
                    raise osv.except_osv(_('Error') + 'R001', _('CODA V%s statements are not supported, please contact your bank') % statement['version'])
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
                        statement['currency'] = rmspaces(line[18:21])
                    elif line[1] == '1':  # foreign bank account BBAN structure
                        raise osv.except_osv(_('Error') + 'R1001', _('Foreign bank accounts with BBAN structure are not supported '))
                    elif line[1] == '2':    # Belgian bank account IBAN structure
                        statement['acc_number'] = rmspaces(line[5:21])
                        statement['currency'] = rmspaces(line[39:42])
                    elif line[1] == '3':    # foreign bank account IBAN structure
                        raise osv.except_osv(_('Error') + 'R1002', _('Foreign bank accounts with IBAN structure are not supported '))
                    else:  # Something else, not supported
                        raise osv.except_osv(_('Error') + 'R1003', _('Unsupported bank account structure '))
                ids = self.pool.get('res.partner.bank').search(cr, uid, [('acc_number', '=', statement['acc_number'])])
                not_found_except = osv.except_osv(_('Error') + 'R1004', _("No matching CODA Bank Account Configuration record found. Please check if the 'Bank Account Number' and 'Currency' fields of your configuration record match with '%s' and '%s'.") % (statement['acc_number'], statement['currency']))
                if ids and len(ids) > 0:
                    bank_accs = self.pool.get('res.partner.bank').browse(cr, uid, ids)
                    for bank_acc in bank_accs:
                        statement['journal_id'] = bank_acc.journal_id
                        if (statement['journal_id'].currency and statement['journal_id'].currency.name != statement['currency']) and (not statement['journal_id'].currency and statement['journal_id'].company_id.currency_id.name != statement['currency']):
                            raise not_found_except
                else:
                    raise not_found_except
                statement['description'] = rmspaces(line[90:125])
                statement['balance_start'] = float(rmspaces(line[43:58])) / 1000
                statement['balance_start_date'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[58:64]), '%d%m%y'))
                statement['accountHolder'] = rmspaces(line[64:90])
                statement['paperSeqNumber'] = rmspaces(line[2:5])
                statement['codaSeqNumber'] = rmspaces(line[125:128])
            elif line[0] == '2':
                if line[1] == '1':
                    #New statement line
                    statementLine = {}
                    statementLine['type'] = 'general'
                    statementLine['ref'] = rmspaces(line[2:10])
                    statementLine['ref_move'] = rmspaces(line[2:6])
                    statementLine['ref_move_detail'] = rmspaces(line[6:10])
                    statementLine['sequence'] = len(statement['lines']) + 1
                    statementLine['transactionRef'] = rmspaces(line[10:31])
                    statementLine['debit'] = line[31]  # 0 = Credit, 1 = Debit
                    statementLine['amount'] = float(rmspaces(line[32:47])) / 1000
                    if statementLine['debit'] == '1':
                        statementLine['amount'] = - statementLine['amount']
                    statementLine['transaction_type'] = line[53]
                    if statementLine['transaction_type'] not in transaction_types:
                        raise osv.except_osv(_('Error') + 'R2001', _('The File contains an invalid CODA Transaction Type : %s') % statementLine['transaction_type'])
                    statementLine['transactionDate'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[47:53]), '%d%m%y'))
                    statementLine['transaction_family'] = rmspaces(line[54:56])
                    statementLine['transaction_code'] = rmspaces(line[56:58])
                    statementLine['transaction_category'] = rmspaces(line[58:61])
                    statementLine['communication'] = rmspaces(line[62:115])
                    statementLine['entryDate'] = rmspaces(line[115:121])
                    statementLine['type'] = 'normal'
                    statementLine['globalisation'] = int(line[124])
                    if len(statement['globalisation_stack']) > 0 and statementLine['communication'] != '':
                        statementLine['communication'] = "\n".join([statement['globalisation_stack'][-1]['communication'], statementLine['communication']])
                    if statementLine['globalisation'] > 0:
                        if len(statement['globalisation_stack']) > 0 and statement['globalisation_stack'][-1]['globalisation'] == statementLine['globalisation']:
                            # Destack
                            statement['globalisation_stack'].pop()
                        else:
                            #Stack
                            statementLine['type'] = 'globalisation'
                            statement['globalisation_stack'].append(statementLine)
                    statement['lines'].append(statementLine)
                elif line[1] == '2':
                    if statement['lines'][-1]['ref'][0:4] != line[2:6]:
                        raise osv.except_osv(_('Error') + 'R2004', _('CODA parsing error on movement data record 2.2, seq nr %s! Please report this issue via your OpenERP support channel.') % line[2:10])
                    statement['lines'][-1]['communication'] += rmspaces(line[10:63])
                    statement['lines'][-1]['payment_reference'] = rmspaces(line[63:98])
                    statement['lines'][-1]['counterparty_bic'] = rmspaces(line[98:109])
                elif line[1] == '3':
                    if statement['lines'][-1]['ref'][0:4] != line[2:6]:
                        raise osv.except_osv(_('Error') + 'R2005', _('CODA parsing error on movement data record 2.3, seq nr %s! Please report this issue via your OpenERP support channel.') % line[2:10])
                    if statement['version'] == '1':
                        statement['lines'][-1]['counterpartyNumber'] = rmspaces(line[10:22])
                        statement['lines'][-1]['counterpartyName'] = rmspaces(line[47:125])
                        statement['lines'][-1]['counterpartyCurrency'] = ''
                    else:
                        if line[22] == ' ':
                            statement['lines'][-1]['counterpartyNumber'] = rmspaces(line[10:22])
                            statement['lines'][-1]['counterpartyCurrency'] = rmspaces(line[23:26])
                        else:
                            statement['lines'][-1]['counterpartyNumber'] = rmspaces(line[10:44])
                            statement['lines'][-1]['counterpartyCurrency'] = rmspaces(line[44:47])
                        statement['lines'][-1]['counterpartyName'] = rmspaces(line[47:82])
                        statement['lines'][-1]['communication'] += rmspaces(line[82:125])
                else:
                    # movement data record 2.x (x != 1,2,3)
                    raise osv.except_osv(_('Error') + 'R2006', _('\nMovement data records of type 2.%s are not supported ') % line[1])
            elif line[0] == '3':
                if line[1] == '1':
                    infoLine = {}
                    infoLine['entryDate'] = statement['lines'][-1]['entryDate']
                    infoLine['type'] = 'information'
                    infoLine['sequence'] = len(statement['lines']) + 1
                    infoLine['ref'] = rmspaces(line[2:10])
                    infoLine['transactionRef'] = rmspaces(line[10:31])
                    infoLine['transaction_type'] = line[31]
                    infoLine['transaction_family'] = rmspaces(line[32:34])
                    infoLine['transaction_code'] = rmspaces(line[34:36])
                    infoLine['transaction_category'] = rmspaces(line[36:39])
                    infoLine['communication'] = rmspaces(line[40:113])
                    infoLine['amount'] = 0.0
                    infoLine['type'] = 'information'
                    statement['lines'].append(infoLine)
                elif line[1] == '2':
                    if infoLine['ref'] != rmspaces(line[2:10]):
                        raise osv.except_osv(_('Error') + 'R3004', _('CODA parsing error on information data record 3.2, seq nr %s! Please report this issue via your OpenERP support channel.') % line[2:10])
                    statement['lines'][-1]['communication'] += rmspaces(line[10:100])
                elif line[1] == '3':
                    if infoLine['ref'] != rmspaces(line[2:10]):
                        raise osv.except_osv(_('Error') + 'R3005', _('CODA parsing error on information data record 3.3, seq nr %s! Please report this issue via your OpenERP support channel.') % line[2:10])
                    statement['lines'][-1]['communication'] += rmspaces(line[10:100])
            elif line[0] == '4':
                    comm_line = {}
                    comm_line['type'] = 'communication'
                    comm_line['sequence'] = len(statement['lines']) + 1
                    comm_line['ref'] = rmspaces(line[2:10])
                    comm_line['communication'] = rmspaces(line[32:112])
                    comm_line['amount'] = 0.0
                    comm_line['type'] = 'communication'
                    statement['lines'].append(comm_line)
            elif line[0] == '8':
                # new balance record
                statement['debit'] = line[41]
                statement['paperSeqNumber'] = rmspaces(line[1:4])
                statement['balance_end_real'] = float(rmspaces(line[42:57])) / 1000
                statement['balance_end_realDate'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[57:63]), '%d%m%y'))
                if statement['debit'] == '1':    # 1=Debit
                    statement['balance_end_real'] = - statement['balance_end_real']
                if statement['balance_end_realDate']:
                    period_id = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', statement['balance_end_realDate']), ('date_stop', '>=', statement['balance_end_realDate'])])
                else:
                    period_id = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', statement['date']), ('date_stop', '>=', statement['date'])])
                if not period_id and len(period_id) == 0:
                    raise osv.except_osv(_('Error') + 'R0002', _("The CODA Statement New Balance date doesn't fall within a defined Accounting Period! Please create the Accounting Period for date %s.") % statement['balance_end_realDate'])
                statement['period_id'] = period_id[0]
            elif line[0] == '9':
                statement['balanceMin'] = float(rmspaces(line[22:37])) / 1000
                statement['balancePlus'] = float(rmspaces(line[37:52])) / 1000
                if not statement['balance_end_real']:
                    statement['balance_end_real'] = statement['balance_start'] + statement['balancePlus'] - statement['balanceMin']
        for i, statement in enumerate(statements):
            data = {
                'name': '[' + statement['date'] + ']' + statement['description'],
                'date': statement['date'],
                'journal_id': statement['journal_id'].id,
                'period_id': statement['period_id'],
                'balance_start': statement['balance_start'],
                'balance_end_real': statement['balance_end_real'],
            }
            statement['id'] = self.pool.get('account.bank.statement').create(cr, uid, data, context=context)
            for line in statement['lines']:
                if line['type'] == 'normal':
                    counterparty = []
                    if 'counterpartyName' in line:
                        counterparty.append(line['counterpartyName'])
                    if 'counterpartyNumber' in line:
                        counterparty.append(line['counterpartyNumber'])
                    if len(counterparty) > 0:
                        counterparty = '[' + ' / '.join(counterparty) + ']'
                    else:
                        counterparty = '/'
                    if line['transaction_type'] in transaction_types:
                        line['transaction_type'] = transaction_types[line['transaction_type']][1]
                    if line['transaction_category'] in transaction_categories:
                        line['transaction_category'] = transaction_categories[line['transaction_category']]
                    if line['transaction_family'] in transaction_codes:
                        transaction_family = transaction_codes[line['transaction_family']]
                        line['transaction_family'] = transaction_family[0]
                        if line['transaction_code'] in transaction_family[1]:
                            line['transaction_code'] = transaction_family[1][line['transaction_code']]
                    note = []
                    note.append(_('Counter Party') + ': ' + counterparty)
                    note.append(_('Communication') + ': ' + line['communication'])
                    note.append(_('Transaction type') + ': ' + line['transaction_type'])
                    note.append(_('Transaction family') + ': ' + line['transaction_family'])
                    note.append(_('Transaction code') + ': ' + line['transaction_code'])
                    note.append(_('Transaction category') + ': ' + line['transaction_category'])

                    try:
                        if 'counterpartyNumber' in line and int(line['counterpartyNumber']) == 0:
                            line['counterpartyNumber'] = False
                    except:
                        pass
                    partner = None
                    partner_id = None
                    if 'counterpartyNumber' in line and line['counterpartyNumber']:
                        ids = self.pool.get('res.partner.bank').search(cr, uid, [('acc_number', '=', str(line['counterpartyNumber']))])
                        if ids and len(ids) > 0:
                            partner = self.pool.get('res.partner.bank').browse(cr, uid, ids[0], context=context).partner_id
                            partner_id = partner.id
                    if partner:
                        if partner.customer:
                            line['type'] = 'customer'
                        else:
                            line['type'] = 'supplier'
                        if line['debit'] == '1':
                            line['account'] = partner.property_account_payable.id
                        else:
                            line['account'] = partner.property_account_receivable.id
                    else:
                        line['type'] = 'general'
                        if line['debit'] == '1':
                            line['account'] = statement['journal_id'].default_debit_account_id.id
                        else:
                            line['account'] = statement['journal_id'].default_credit_account_id.id
                            

                    data = {
                        'name': line['communication'],
                        'note':  "\n".join(note),
                        'date': line['entryDate'],
                        'amount': line['amount'],
                        'type': line['type'],
                        'partner_id': partner_id,
                        'account_id': line['account'],
                        'statement_id': statement['id'],
                        'ref': line['ref'],
                        'sequence': line['sequence'],
                    }
                    self.pool.get('account.bank.statement.line').create(cr, uid, data, context=context)

account_coda_import()

transaction_types = {
    "0": ["", "Simple amount without detailed data; e.g. : an individual credit transfer [free of charges]."],
    "1": ["", "Amount as totalised by the customer; e.g. a file regrouping payments of wages or payments made to suppliers or a file regrouping collections for which the customer is ]debited or credited with one single amount. As a matter of principle, this type is also used when no detailed data is following [type 5]."],
    "5": ["1", "Detail of 1. Standard procedure is no detailing. However, the customer may ask for detailed data to be included into his file after the overall record [type 1]."],
    "2": ["", "Amount as totalised by the bank; e.g. : the total amount of a series of credit transfers with a structured communication As a matter of principle, this type will also be used when no detailed data [type 6 or 7] is following."],
    "6": ["2", "Detail of 2. Simple amount without detailed data. Normally, data of this kind comes after type 2. The customer may ask for a separate file containing the detailed data. In that case, one will speak of a ‘separate application’. The records in a separate application keep type 6."],
    "7": ["2", "Detail of 2. Simple account with detailed data The records in a separate application keep type 7."],
    "9": ["7", "Detail of 7. The records in a separate application keep type 9."],
    "3": ["", "Simple amount with detailed data; e.g. in case of charges for cross-border credit transfers."],
    "8": ["3", "Detail of 3."],
}

transaction_codes = {
    "00": ["Undefined transactions", {
        "89": "Cancellation of a transaction",
        "87": "Costs refunded",
        "85": "Correction",
        "83": "Value correction",
        "39": "Cancellation of a transaction",
        "37": "Costs",
        "35": "Correction",
        "33": "Value correction",
        "00": "Undefined transaction",
        }],
    "01": ["Domestic or local SEPA credit transfers", {
        "99": "Cancellation or correction",
        "87": "Reimbursement of costs",
        "66": "Financial centralization",
        "64": "Transfer to your account",
        "62": "Unpaid postal order",
        "60": "Non-presented circular cheque",
        "54": "Unexecutable transfer order",
        "52": "Payment in your favour",
        "51": "Transfer in your favour – initiated by the bank",
        "50": "Transfer in your favour",
        "49": "Cancellation or correction",
        "39": "Your issue circular cheque",
        "37": "Costs",
        "17": "Financial centralisation",
        "15": "Balance due insurance premium",
        "13": "Transfer from your account",
        "11": "Your semi-standing order – payment to employees",
        "09": "Your semi-standing order",
        "07": "Collective transfer",
        "05": "Payment of wages etc.",
        "03": "Standing order",
        "02": "Individual transfer order initiated by the bank",
        "01": "Individual transfer order",
        }],
    "03": ["Cheques", {
        "99": "Cancellation or correction",
        "87": "Reimbursement of cheque-related costs",
        "68": "Credit of a payment via electronic purse",
        "66": "Remittance of cheque by your branch - credit under usual reserve",
        "64": "Reversal of settlement of credit card",
        "63": "Second credit of unpaid cheque",
        "62": "Reversal of cheque",
        "60": "Reversal of voucher",
        "58": "Remittance of cheques, vouchers, etc. credit after collection",
        "56": "Non-presented certified cheques",
        "52": "First credit of cheques, vouchers, luncheon vouchers, postal orders, credit under usual reserve",
        "50": "Credit of a payment via terminal",
        "49": "Cancellation or correction",
        "39": "Provisionally unpaid due to other reason than manual presentation",
        "38": "Provisionally unpaid",
        "37": "Cheque-related costs",
        "35": "Cash advance",
        "19": "Settlement of credit cards",
        "17": "Your certified cheque",
        "15": "Your purchase bank cheque",
        "13": "Eurocheque written out abroad",
        "11": "Department store cheque",
        "09": "Unpaid voucher",
        "07": "Definitely unpaid cheque",
        "05": "Payment of voucher",
        "03": "Your purchase by payment card",
        "01": "Payment of your cheque",
        }],
    "04": ["Cards", {
        "99": "Cancellation or correction",
        "87": "Reimbursement of costs",
        "68": "Credit after Proton payments",
        "55": "Income from payments by GSM",
        "53": "Cash deposit at an ATM",
        "52": "Loading GSM cards",
        "51": "Unloading Proton",
        "50": "Credit after a payment at a terminal",
        "49": "Cancellation or correction",
        "37": "Costs",
        "08": "Payment by means of a payment card outside the Eurozone",
        "07": "Payment by GSM",
        "06": "Payment with tank card",
        "05": "Loading Proton",
        "04": "Cash withdrawal from an ATM",
        "03": "Settlement credit cards",
        "02": "Payment by means of a payment card within the Eurozone",
        "01": "Loading a GSM card",
        }],
    "05": ["Direct debit", {
        "99": "Cancellation or correction",
        "87": "Reimbursement of costs",
        "58": "Reversal",
        "56": "Unexecutable reimbursement",
        "54": "Reimbursement",
        "52": "Credit under usual reserve",
        "50": "Credit after collection",
        "49": "Cancellation or correction",
        "37": "Costs",
        "05": "Reimbursement",
        "03": "Unpaid debt",
        "01": "Payment",
        }],
    "07": ["Domestic commercial paper", {
        "99": "Cancellation or correction",
        "87": "Reimbursement of costs",
        "86": "Payment after cession",
        "64": "Warrant",
        "58": "Remittance of supplier's bill without guarantee",
        "56": "Remittance of supplier's bill with guarantee",
        "54": "Remittance of commercial paper for discount",
        "52": "Remittance of commercial paper - credit under usual reserve",
        "50": "Remittance of commercial paper - credit after collection",
        "49": "Cancellation or correction",
        "39": "Return of an irregular bill of exchange",
        "37": "Costs related to commercial paper",
        "14": "Warrant fallen due",
        "12": "Safe custody",
        "10": "Renewal of agreed maturity date",
        "09": "Agio on supplier's bill",
        "08": "Payment in advance",
        "07": "Unpaid commercial paper",
        "06": "Extension of maturity date",
        "05": "Commercial paper claimed back",
        "03": "Payment receipt card",
        "01": "Payment commercial paper",
        }],
    "09": ["Counter transactions", {
        "99": "Cancellation or correction",
        "87": "Reimbursement of costs",
        "70": "Sale of traveller’s cheque",
        "68": "Difference in payment",
        "66": "Repurchase of petrol coupons",
        "64": "Your winning lottery ticket",
        "62": "Sale of gold/pieces under usual reserve",
        "60": "Sale of foreign bank notes",
        "58": "Payment by your branch/agents",
        "56": "Reserve",
        "54": "Your payment ATM",
        "52": "Payment night safe",
        "50": "Cash payment",
        "49": "Cancellation or correction",
        "37": "Costs",
        "25": "Purchase of traveller’s cheque",
        "21": "Cash withdrawal on card (PROTON)",
        "19": "Difference in payment",
        "17": "Purchase of fiscal stamps",
        "15": "Your purchase of lottery tickets",
        "13": "Cash withdrawal by your branch or agents",
        "11": "Your purchase of luncheon vouchers",
        "09": "Purchase of petrol coupons",
        "07": "Purchase of gold/pieces",
        "05": "Purchase of foreign bank notes",
        "03": "Cash withdrawal by card (ATM)",
        "01": "Cash withdrawal",
        }],
    "11": ["Securities", {
        "99": "Cancellation or correction",
        "87": "Reimbursement of costs",
        "70": "Settlement of securities",
        "68": "Compensation for missing coupon",
        "66": "Retrocession of issue commission",
        "64": "Your issue",
        "62": "Interim interest on subscription",
        "58": "Repayable securities from a deposit or delivered at the counter - credit under usual reserve",
        "56": "Reserve",
        "52": "Payment of coupons from a deposit or settlement of coupons delivered over the counter - credit under usual reserve",
        "51": "Tender",
        "50": "Sale of securities",
        "49": "Cancellation or correction",
        "37": "Costs",
        "19": "Regularisation costs",
        "17": "Management fee",
        "15": "Interim interest on subscription",
        "13": "Your repurchase of issue",
        "11": "Payable coupons/repayable securities",
        "09": "Settlement of securities",
        "06": "Share option plan – exercising an option",
        "05": "Partial payment subscription",
        "04": "Issues",
        "03": "Subscription to securities",
        "02": "Tenders",
        "01": "Purchase of securities",
        }],
    "13": ["Credit", {
        "99": "Cancellation or correction",
        "87": "Reimbursement of costs",
        "70": "Settlement of discount bank acceptance",
        "68": "Documentary export credits",
        "62": "Term loan",
        "60": "Settlement of mortgage loan",
        "56": "Subsidy",
        "55": "Fixed advance – interest only",
        "54": "Fixed advance – capital and interest",
        "50": "Settlement of instalment credit",
        "49": "Cancellation or correction",
        "37": "Credit-related costs",
        "21": "Other credit applications",
        "19": "Documentary import credits",
        "15": "Your repayment hire-purchase and similar claims",
        "13": "Settlement of bank acceptances",
        "11": "Your repayment mortgage loan",
        "07": "Your repayment instalment credits",
        "05": "Settlement of fixed advance",
        "02": "Long-term loan",
        "01": "Short-term loan",
        }],
    "30": ["Various transactions", {
        "99": "Cancellation or correction",
        "89": "Undefined transaction",
        "87": "Reimbursement of costs",
        "83": "Value (date) correction",
        "55": "Interest term investment",
        "54": "Capital and/or interest term investment",
        "52": "Forward sale of foreign exchange",
        "50": "Spot sale of foreign exchange",
        "49": "Cancellation or correction",
        "39": "Undefined transaction",
        "37": "Costs",
        "33": "Value (date) correction",
        "05": "Capital and/or interest term investment",
        "03": "Forward purchase of foreign exchange",
        "01": "Spot purchase of foreign exchange",
        }],
    "35": ["Closing (periodical settlements for interest, costs,…)", {
        "99": "Cancellation or correction",
        "87": "Reimbursement of costs",
        "50": "Closing",
        "49": "Cancellation or correction",
        "37": "Costs",
        "01": "Closing",
        }],
    "41": ["International credit transfers - non-SEPA credit transfers", {
        "99": "Cancellation or correction",
        "87": "Reimbursement of costs",
        "66": "Financial centralisation (credit)",
        "64": "Transfer to your account",
        "50": "Transfer",
        "49": "Cancellation or correction",
        "38": "Costs relating to incoming foreign and non-SEPA transfers",
        "37": "Costs relating to outgoing foreign transfers and non-SEPA transfers",
        "17": "Financial centralisation (debit)",
        "13": "Transfer from your account",
        "07": "Collective transfers",
        "05": "Collective payments of wages",
        "03": "Standing order",
        "01": "Transfer",
        }],
    "43": ["Foreign cheques", {
        "99": "Cancellation or correction",
        "87": "Reimbursement of costs",
        "70": "Purchase of traveller’s cheque",
        "62": "Reversal of cheques",
        "58": "Remittance of foreign cheque credit after collection",
        "52": "Remittance of foreign cheque credit under usual reserve",
        "49": "Cancellation or correction",
        "37": "Costs relating to payment of foreign cheques",
        "15": "Purchase of an international bank cheque",
        "07": "Unpaid foreign cheque",
        "01": "Payment of a foreign cheque",
        }],
    "47": ["Foreign commercial paper", {
        "99": "Cancellation or correction",
        "87": "Reimbursement of costs",
        "64": "Warrant",
        "62": "Remittance of documents abroad - credit after collection",
        "60": "Remittance of documents abroad - credit under usual reserve",
        "58": "Idem without guarantee",
        "56": "Remittance of guaranteed foreign supplier's bill",
        "54": "Discount abroad",
        "52": "Remittance of foreign bill credit under usual reserve",
        "50": "Remittance of foreign bill credit after collection",
        "49": "Cancellation or correction",
        "37": "Costs relating to the payment of a foreign bill",
        "14": "Warrant fallen due",
        "13": "Discount foreign supplier's bills",
        "11": "Payment documents abroad",
        "07": "Unpaid foreign bill",
        "06": "Extension",
        "05": "Bill claimed back",
        "01": "Payment of foreign bill",
        }],
    "49": ["Foreign counter transactions", {"03": "ATM withdrawal"}],
    "80": ["Separately charged costs and provisions", {
        "01": "Guarantee card charges",
        "02": "Costs relating to electronic output",
        "03": "Payment card charges",
        "04": "Costs for holding a documentary cash credit",
        "05": "Card charges",
        "06": "Damage relating to bills and cheques",
        "07": "Insurance costs",
        "08": "Registering compensation for savings accounts",
        "09": "Postage",
        "10": "Purchase of Smartcard",
        "11": "Costs for the safe custody of correspondence",
        "12": "Costs for opening a bank guarantee",
        "13": "Renting of safes",
        "14": "Handling costs instalment credit",
        "15": "Night safe",
        "16": "Bank confirmation to revisor or accountant",
        "17": "Charge for safe custody",
        "18": "Trade information",
        "19": "Special charge for safe custody",
        "20": "Drawing up a certificate",
        "21": "Pay-packet charges",
        "22": "Management/custody",
        "23": "Research costs",
        "24": "Participation in and management of interest refund system",
        "25": "Renting of direct debit box",
        "26": "Travel insurance premium",
        "27": "Subscription fee",
        "29": "Information charges",
        "31": "Writ service fee",
        "33": "Miscellaneous fees and commissions",
        "35": "Costs",
        "37": "Access right to database",
        "39": "Surety fee",
        "41": "Research costs",
        "43": "Printing of forms",
        "45": "Documentary credit charges",
        "47": "Charging fees for transactions",
        "49": "Cancellation or correction",
        "99": "Cancellation or correction",
        }],
}

transaction_categories = {
    "000": "Net amount",
    "001": "Interest received",
    "002": "Interest paid",
    "003": "Credit commission",
    "004": "Postage",
    "005": "Renting of letterbox",
    "006": "Various fees/commissions",
    "007": "Access right to database",
    "008": "Information charges",
    "009": "Travelling expenses",
    "010": "Writ service fee",
    "011": "VAT",
    "012": "Exchange commission",
    "013": "Payment commission",
    "014": "Collection commission",
    "015": "Correspondent charges",
    "016": "BLIW/IBLC dues",
    "017": "Research costs",
    "018": "Tental guarantee charges",
    "019": "Tax on physical delivery",
    "020": "Costs of physical delivery",
    "021": "Costs for drawing up a bank cheque",
    "022": "Priority costs",
    "023": "Exercising fee",
    "024": "Growth premium",
    "025": "Individual entry for exchange charges",
    "026": "Handling commission",
    "027": "Charges for unpaid bills",
    "028": "Fidelity premium",
    "029": "Protest charges",
    "030": "Account insurance",
    "031": "Charges foreign cheque",
    "032": "Drawing up a circular cheque",
    "033": "Charges for a foreign bill",
    "034": "Reinvestment fee",
    "035": "Charges foreign documentary bill",
    "036": "Costs relating to a refused cheque",
    "037": "Commission for handling charges",
    "039": "Telecommunications",
    "041": "Credit card costs",
    "042": "Payment card costs",
    "043": "Insurance costs",
    "045": "Handling costs",
    "047": "Charges extension bill",
    "049": "Fiscal stamps/stamp duty",
    "050": "Capital term investment",
    "051": "Withholding tax",
    "052": "Residence state tax",
    "053": "Printing of forms",
    "055": "Repayment loan or credit capital",
    "057": "Interest subsidy",
    "058": "Capital premium",
    "059": "Default interest",
    "061": "Charging fees for transactions",
    "063": "Rounding differences",
    "065": "Interest payment advice",
    "066": "Fixed loan advance - reimbursement",
    "067": "Fixed loan advance - extension",
    "068": "Countervalue of an entry",
    "069": "Forward arbitrage contracts : sum to be supplied by customer",
    "070": "Forward arbitrage contracts : sum to be supplied by bank",
    "071": "Fixed loan advance - availability",
    "072": "Countervalue of commission to third party",
    "073": "Costs of ATM abroad",
    "074": "Mailing costs",
    "100": "Gross amount",
    "200": "Overall documentary credit charges",
    "201": "Advice notice commission",
    "202": "Advising commission | Additional advising commission",
    "203": "Confirmation fee | Additional confirmation fee | Commitment fee | Flat fee | Confirmation reservation commission | Additional reservation commission",
    "204": "Amendment fee",
    "205": "Documentary payment commission | Document commission | Drawdown fee | Negotiation fee",
    "206": "Surety fee/payment under reserve",
    "207": "Non-conformity fee",
    "208": "Commitment fee deferred payment",
    "209": "Transfer commission",
    "210": "Commitment fee",
    "211": "Credit arrangement fee | Additional credit arrangement fee",
    "212": "Warehousing fee",
    "213": "Financing fee",
    "214": "Issue commission (delivery order)",
    "400": "Acceptance fee",
    "401": "Visa charges",
    "402": "Certification costs",
    "403": "Minimum discount rate",
    "404": "Discount commission",
    "405": "Bill guarantee commission",
    "406": "Collection charges",
    "407": "Costs Article 45",
    "408": "Cover commission",
    "409": "Safe deposit charges",
    "410": "Reclamation charges",
    "411": "Fixed collection charge",
    "412": "Advice of expiry charges",
    "413": "Acceptance charges",
    "414": "Regularisation charges",
    "415": "Surety fee",
    "416": "Charges for the deposit of security",
    "418": "Endorsement commission",
    "419": "Bank service fee",
    "420": "Retention charges",
    "425": "Foreign broker's commission",
    "426": "Belgian broker's commission",
    "427": "Belgian Stock Exchange tax",
    "428": "Interest accrued",
    "429": "Foreign Stock Exchange tax",
    "430": "Recovery of foreign tax",
    "431": "Delivery of a copy",
}


def rmspaces(s):
    return " ".join(s.split())



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
