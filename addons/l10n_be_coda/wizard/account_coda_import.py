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
            print
            codafile = str(codafile)
            codafilename = codafilename
        else:
            data = self.browse(cr, uid, ids)[0]
            try:
                codafile = data.coda_data
                codafilename = data.coda_fname
            except:
                raise osv.except_osv(_('Error!'), _('Wizard in incorrect state. Please hit the Cancel button!'))
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
                    raise osv.except_osv(_('Error R001!'), _('CODA V%s statements are not supported, please contact your bank!') % statement['version'])
                statement['globalisation_stack'] = []
                statement['lines'] = []
                statement['date'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[5:11]), '%d%m%y'))
                statement['separateApplication'] = rmspaces(line[83:88])
            elif line[0] == '1':
                #Statement details
                if statement['version'] == '1':
                    statement['accountNumber'] = rmspaces(line[5:17])
                    statement['currency'] = rmspaces(line[18:21])
                elif statement['version'] == '2':
                    if line[1] == '0':  # Belgian bank account BBAN structure
                        statement['accountNumber'] = rmspaces(line[5:17])
                        statement['currency'] = rmspaces(line[18:21])
                    elif line[1] == '1':  # foreign bank account BBAN structure
                        raise osv.except_osv(_('Error R1001!'), _('Foreign bank accounts with BBAN structure are not supported !'))
                    elif line[1] == '2':    # Belgian bank account IBAN structure
                        statement['accountNumber'] = rmspaces(line[5:21])
                        statement['currency'] = rmspaces(line[39:42])
                    elif line[1] == '3':    # foreign bank account IBAN structure
                        raise osv.except_osv(_('Error R1002!'), _('Foreign bank accounts with IBAN structure are not supported !'))
                    else:  # Something else, not supported
                        raise osv.except_osv(_('Error R1003!'), _('Unsupported bank account structure !'))
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
                        raise osv.except_osv(_('Error R2001!'), _('The File contains an invalid CODA Transaction Type : %s!') % statementLine['transaction_type'])
                    statementLine['transactionDate'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[47:53]), '%d%m%y'))
                    statementLine['transaction_family'] = rmspaces(line[54:56])
                    #TODO Handling severals transactions Family
                    statementLine['transaction_code'] = rmspaces(line[56:58])
                    #TODO Handling severals transactions code
                    statementLine['transaction_category'] = rmspaces(line[58:61])
                    #TODO Handling severals transactions category
                    statementLine['communication'] = rmspaces(line[62:115])
                    #TODO Handling structured communication
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
                        raise osv.except_osv(_('Error R2004!'), _('CODA parsing error on movement data record 2.2, seq nr %s! Please report this issue via your OpenERP support channel.') % line[2:10])
                    statement['lines'][-1]['communication'] += rmspaces(line[10:63])
                    statement['lines'][-1]['payment_reference'] = rmspaces(line[63:98])
                    statement['lines'][-1]['counterparty_bic'] = rmspaces(line[98:109])
                elif line[1] == '3':
                    if statement['lines'][-1]['ref'][0:4] != line[2:6]:
                        raise osv.except_osv(_('Error R2005!'), _('CODA parsing error on movement data record 2.3, seq nr %s! Please report this issue via your OpenERP support channel.') % line[2:10])
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
                    raise osv.except_osv(_('Error R2009!'), _('\nMovement data records of type 2.%s are not supported !') % line[1])
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
                        raise osv.except_osv(_('Error R3004!'), _('CODA parsing error on information data record 3.2, seq nr %s! Please report this issue via your OpenERP support channel.') % line[2:10])
                    statement['lines'][-1]['communication'] += rmspaces(line[10:100])
                elif line[1] == '3':
                    if infoLine['ref'] != rmspaces(line[2:10]):
                        raise osv.except_osv(_('Error R3005!'), _('CODA parsing error on information data record 3.3, seq nr %s! Please report this issue via your OpenERP support channel.') % line[2:10])
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
                    raise osv.except_osv(_('Error R0002!'), _("The CODA Statement New Balance date doesn't fall within a defined Accounting Period! Please create the Accounting Period for date %s.") % statement['balance_end_realDate'])
                statement['period_id'] = period_id[0]
            elif line[0] == '9':
                statement['balanceMin'] = float(rmspaces(line[22:37])) / 1000
                statement['balancePlus'] = float(rmspaces(line[37:52])) / 1000
                if not statement['balance_end_real']:
                    statement['balance_end_real'] = statement['balance_start'] + statement['balancePlus'] - statement['balanceMin']
        for i, statement in enumerate(statements):
            # print '---STATEMENT #' + str(i) + '---'
            print statement
            data = {
                'name': '[' + statement['date'] + ']' + statement['description'],
                'date': statement['date'],
                'journal_id': 18,
                'period_id': statement['period_id'],
                'balance_start': statement['balance_start'],
                'balance_end_real': statement['balance_end_real'],
                'account_id': 1
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
                    partner_id = None
                    if 'counterpartyNumber' in line and line['counterpartyNumber']:
                        ids = self.pool.get('res.partner.bank').search(cr, uid, [('acc_number', '=', str(line['counterpartyNumber']))])
                        if ids and len(ids) > 0:
                            partner_id = self.pool.get('res.partner.bank').browse(cr, uid, ids[0],context=context).partner_id.id
                        else:
                            partner_id = None

                    data = {
                        'name': line['communication'],
                        'note':  "\n".join(note),
                        'date': line['entryDate'],
                        'amount': line['amount'],
                        #  'type': '',
                        'partner_id': partner_id,
                        'account_id': 1,
                        'statement_id': statement['id'],
                        #  'analytic_account_id': '',
                        #  'move_ids': '',
                        'ref': line['ref'],
                        'sequence': line['sequence'],
                    }
                    self.pool.get('account.bank.statement.line').create(cr, uid, data, context=context)

account_coda_import()

transaction_types = {
    "0": ["", _("Simple amount without detailed data; e.g. : an individual credit transfer [free of charges].")],
    "1": ["", _("Amount as totalised by the customer; e.g. a file regrouping payments of wages or payments made to suppliers or a file regrouping collections for which the customer is ]debited or credited with one single amount. As a matter of principle, this type is also used when no detailed data is following [type 5].")],
    "5": ["1", _("Detail of 1. Standard procedure is no detailing. However, the customer may ask for detailed data to be included into his file after the overall record [type 1].")],
    "2": ["", _("Amount as totalised by the bank; e.g. : the total amount of a series of credit transfers with a structured communication As a matter of principle, this type will also be used when no detailed data [type 6 or 7] is following.")],
    "6": ["2", _("Detail of 2. Simple amount without detailed data. Normally, data of this kind comes after type 2. The customer may ask for a separate file containing the detailed data. In that case, one will speak of a ‘separate application’. The records in a separate application keep type 6.")],
    "7": ["2", _("Detail of 2. Simple account with detailed data The records in a separate application keep type 7.")],
    "9": ["7", _("Detail of 7. The records in a separate application keep type 9.")],
    "3": ["", _("Simple amount with detailed data; e.g. in case of charges for cross-border credit transfers.")],
    "8": ["3", _("Detail of 3.")],
}

transaction_codes = {
    "00": [_("Undefined transactions"), {
        "89": _("Cancellation of a transaction"),
        "87": _("Costs refunded"),
        "85": _("Correction"),
        "83": _("Value correction"),
        "39": _("Cancellation of a transaction"),
        "37": _("Costs"),
        "35": _("Correction"),
        "33": _("Value correction"),
        "00": _("Undefined transaction")
        }],
    "01": [_("Domestic or local SEPA credit transfers"), {
        "99": _("Cancellation or correction"),
        "87": _("Reimbursement of costs"),
        "66": _("Financial centralization"),
        "64": _("Transfer to your account"),
        "62": _("Unpaid postal order"),
        "60": _("Non-presented circular cheque"),
        "54": _("Unexecutable transfer order"),
        "52": _("Payment in your favour"),
        "51": _("Transfer in your favour – initiated by the bank"),
        "50": _("Transfer in your favour"),
        "49": _("Cancellation or correction"),
        "39": _("Your issue circular cheque"),
        "37": _("Costs"),
        "17": _("Financial centralisation"),
        "15": _("Balance due insurance premium"),
        "13": _("Transfer from your account"),
        "11": _("Your semi-standing order – payment to employees"),
        "09": _("Your semi-standing order"),
        "07": _("Collective transfer"),
        "05": _("Payment of wages etc."),
        "03": _("Standing order"),
        "02": _("Individual transfer order initiated by the bank"),
        "01": _("Individual transfer order]"),
        }],
    "03": [_("Cheques"), {
        "99": _("Cancellation or correction"),
        "87": _("Reimbursement of cheque-related costs"),
        "68": _("Credit of a payment via electronic purse"),
        "66": _("Remittance of cheque by your branch - credit under usual reserve"),
        "64": _("Reversal of settlement of credit card"),
        "63": _("Second credit of unpaid cheque"),
        "62": _("Reversal of cheque"),
        "60": _("Reversal of voucher"),
        "58": _("Remittance of cheques, vouchers, etc. credit after collection"),
        "56": _("Non-presented certified cheques"),
        "52": _("First credit of cheques, vouchers, luncheon vouchers, postal orders, credit under usual reserve"),
        "50": _("Credit of a payment via terminal"),
        "49": _("Cancellation or correction"),
        "39": _("Provisionally unpaid due to other reason than manual presentation"),
        "38": _("Provisionally unpaid"),
        "37": _("Cheque-related costs"),
        "35": _("Cash advance"),
        "19": _("Settlement of credit cards"),
        "17": _("Your certified cheque"),
        "15": _("Your purchase bank cheque"),
        "13": _("Eurocheque written out abroad"),
        "11": _("Department store cheque"),
        "09": _("Unpaid voucher"),
        "07": _("Definitely unpaid cheque"),
        "05": _("Payment of voucher"),
        "03": _("Your purchase by payment card"),
        "01": _("Payment of your cheque"),
        }],
    "04": [_("Cards"), {
        "99": _("Cancellation or correction"),
        "87": _("Reimbursement of costs"),
        "68": _("Credit after Proton payments"),
        "55": _("Income from payments by GSM"),
        "53": _("Cash deposit at an ATM"),
        "52": _("Loading GSM cards"),
        "51": _("Unloading Proton"),
        "50": _("Credit after a payment at a terminal"),
        "49": _("Cancellation or correction"),
        "37": _("Costs"),
        "08": _("Payment by means of a payment card outside the Eurozone"),
        "07": _("Payment by GSM"),
        "06": _("Payment with tank card"),
        "05": _("Loading Proton"),
        "04": _("Cash withdrawal from an ATM"),
        "03": _("Settlement credit cards"),
        "02": _("Payment by means of a payment card within the Eurozone"),
        "01": _("Loading a GSM card"),
        }],
    "05": [_("Direct debit"), {
        "99": _("Cancellation or correction"),
        "87": _("Reimbursement of costs"),
        "58": _("Reversal"),
        "56": _("Unexecutable reimbursement"),
        "54": _("Reimbursement"),
        "52": _("Credit under usual reserve"),
        "50": _("Credit after collection"),
        "49": _("Cancellation or correction"),
        "37": _("Costs"),
        "05": _("Reimbursement"),
        "03": _("Unpaid debt"),
        "01": _("Payment"),
        }],
    "07": [_("Domestic commercial paper"), {
        "99": _("Cancellation or correction"),
        "87": _("Reimbursement of costs"),
        "86": _("Payment after cession"),
        "64": _("Warrant"),
        "58": _("Remittance of supplier's bill without guarantee"),
        "56": _("Remittance of supplier's bill with guarantee"),
        "54": _("Remittance of commercial paper for discount"),
        "52": _("Remittance of commercial paper - credit under usual reserve"),
        "50": _("Remittance of commercial paper - credit after collection"),
        "49": _("Cancellation or correction"),
        "39": _("Return of an irregular bill of exchange"),
        "37": _("Costs related to commercial paper"),
        "14": _("Warrant fallen due"),
        "12": _("Safe custody"),
        "10": _("Renewal of agreed maturity date"),
        "09": _("Agio on supplier's bill"),
        "08": _("Payment in advance"),
        "07": _("Unpaid commercial paper"),
        "06": _("Extension of maturity date"),
        "05": _("Commercial paper claimed back"),
        "03": _("Payment receipt card"),
        "01": _("Payment commercial paper"),
        }],
    "09": [_("Counter transactions"), {
        "99": _("Cancellation or correction"),
        "87": _("Reimbursement of costs"),
        "70": _("Sale of traveller’s cheque"),
        "68": _("Difference in payment"),
        "66": _("Repurchase of petrol coupons"),
        "64": _("Your winning lottery ticket"),
        "62": _("Sale of gold/pieces under usual reserve"),
        "60": _("Sale of foreign bank notes"),
        "58": _("Payment by your branch/agents"),
        "56": _("Reserve"),
        "54": _("Your payment ATM"),
        "52": _("Payment night safe"),
        "50": _("Cash payment"),
        "49": _("Cancellation or correction"),
        "37": _("Costs"),
        "25": _("Purchase of traveller’s cheque"),
        "21": _("Cash withdrawal on card (PROTON)"),
        "19": _("Difference in payment"),
        "17": _("Purchase of fiscal stamps"),
        "15": _("Your purchase of lottery tickets"),
        "13": _("Cash withdrawal by your branch or agents"),
        "11": _("Your purchase of luncheon vouchers"),
        "09": _("Purchase of petrol coupons"),
        "07": _("Purchase of gold/pieces"),
        "05": _("Purchase of foreign bank notes"),
        "03": _("Cash withdrawal by card (ATM)"),
        "01": _("Cash withdrawal"),
        }],
    "11": [_("Securities"), {
        "99": _("Cancellation or correction"),
        "87": _("Reimbursement of costs"),
        "70": _("Settlement of securities"),
        "68": _("Compensation for missing coupon"),
        "66": _("Retrocession of issue commission"),
        "64": _("Your issue"),
        "62": _("Interim interest on subscription"),
        "58": _("Repayable securities from a deposit or delivered at the counter - credit under usual reserve"),
        "56": _("Reserve"),
        "52": _("Payment of coupons from a deposit or settlement of coupons delivered over the counter - credit under usual reserve"),
        "51": _("Tender"),
        "50": _("Sale of securities"),
        "49": _("Cancellation or correction"),
        "37": _("Costs"),
        "19": _("Regularisation costs"),
        "17": _("Management fee"),
        "15": _("Interim interest on subscription"),
        "13": _("Your repurchase of issue"),
        "11": _("Payable coupons/repayable securities"),
        "09": _("Settlement of securities"),
        "06": _("Share option plan – exercising an option"),
        "05": _("Partial payment subscription"),
        "04": _("Issues"),
        "03": _("Subscription to securities"),
        "02": _("Tenders"),
        "01": _("Purchase of securities"),
        }],
    "13": [_("Credit"), {
        "99": _("Cancellation or correction"),
        "87": _("Reimbursement of costs"),
        "70": _("Settlement of discount bank acceptance"),
        "68": _("Documentary export credits"),
        "62": _("Term loan"),
        "60": _("Settlement of mortgage loan"),
        "56": _("Subsidy"),
        "55": _("Fixed advance – interest only"),
        "54": _("Fixed advance – capital and interest"),
        "50": _("Settlement of instalment credit"),
        "49": _("Cancellation or correction"),
        "37": _("Credit-related costs"),
        "21": _("Other credit applications"),
        "19": _("Documentary import credits"),
        "15": _("Your repayment hire-purchase and similar claims"),
        "13": _("Settlement of bank acceptances"),
        "11": _("Your repayment mortgage loan"),
        "07": _("Your repayment instalment credits"),
        "05": _("Settlement of fixed advance"),
        "02": _("Long-term loan"),
        "01": _("Short-term loan"),
        }],
    "30": [_("Various transactions"), {
        "99": _("Cancellation or correction"),
        "89": _("Undefined transaction"),
        "87": _("Reimbursement of costs"),
        "83": _("Value (date) correction"),
        "55": _("Interest term investment"),
        "54": _("Capital and/or interest term investment"),
        "52": _("Forward sale of foreign exchange"),
        "50": _("Spot sale of foreign exchange"),
        "49": _("Cancellation or correction"),
        "39": _("Undefined transaction"),
        "37": _("Costs"),
        "33": _("Value (date) correction"),
        "05": _("Capital and/or interest term investment"),
        "03": _("Forward purchase of foreign exchange"),
        "01": _("Spot purchase of foreign exchange"),
        }],
    "35": [_("Closing (periodical settlements for interest, costs,…)"), {
        "99": _("Cancellation or correction"),
        "87": _("Reimbursement of costs"),
        "50": _("Closing"),
        "49": _("Cancellation or correction"),
        "37": _("Costs"),
        "01": _("Closing"),
        }],
    "41": [_("International credit transfers - non-SEPA credit transfers"), {
        "99": _("Cancellation or correction"),
        "87": _("Reimbursement of costs"),
        "66": _("Financial centralisation (credit)"),
        "64": _("Transfer to your account"),
        "50": _("Transfer"),
        "49": _("Cancellation or correction"),
        "38": _("Costs relating to incoming foreign and non-SEPA transfers"),
        "37": _("Costs relating to outgoing foreign transfers and non-SEPA transfers"),
        "17": _("Financial centralisation (debit)"),
        "13": _("Transfer from your account"),
        "07": _("Collective transfers"),
        "05": _("Collective payments of wages"),
        "03": _("Standing order"),
        "01": _("Transfer"),
        }],
    "43": [_("Foreign cheques"), {
        "99": _("Cancellation or correction"),
        "87": _("Reimbursement of costs"),
        "70": _("Purchase of traveller’s cheque"),
        "62": _("Reversal of cheques"),
        "58": _("Remittance of foreign cheque credit after collection"),
        "52": _("Remittance of foreign cheque credit under usual reserve"),
        "49": _("Cancellation or correction"),
        "37": _("Costs relating to payment of foreign cheques"),
        "15": _("Purchase of an international bank cheque"),
        "07": _("Unpaid foreign cheque"),
        "01": _("Payment of a foreign cheque"),
        }],
    "47": [_("Foreign commercial paper"), {
        "99": _("Cancellation or correction"),
        "87": _("Reimbursement of costs"),
        "64": _("Warrant"),
        "62": _("Remittance of documents abroad - credit after collection"),
        "60": _("Remittance of documents abroad - credit under usual reserve"),
        "58": _("Idem without guarantee"),
        "56": _("Remittance of guaranteed foreign supplier's bill"),
        "54": _("Discount abroad"),
        "52": _("Remittance of foreign bill credit under usual reserve"),
        "50": _("Remittance of foreign bill credit after collection"),
        "49": _("Cancellation or correction"),
        "37": _("Costs relating to the payment of a foreign bill"),
        "14": _("Warrant fallen due"),
        "13": _("Discount foreign supplier's bills"),
        "11": _("Payment documents abroad"),
        "07": _("Unpaid foreign bill"),
        "06": _("Extension"),
        "05": _("Bill claimed back"),
        "01": _("Payment of foreign bill"),
        }],
    "49": [_("Foreign counter transactions"), {"03": _("ATM withdrawal")}],
    "80": [_("Separately charged costs and provisions"), {
        "01": _("Guarantee card charges"),
        "02": _("Costs relating to electronic output"),
        "03": _("Payment card charges"),
        "04": _("Costs for holding a documentary cash credit"),
        "05": _("Card charges"),
        "06": _("Damage relating to bills and cheques"),
        "07": _("Insurance costs"),
        "08": _("Registering compensation for savings accounts"),
        "09": _("Postage"),
        "10": _("Purchase of Smartcard"),
        "11": _("Costs for the safe custody of correspondence"),
        "12": _("Costs for opening a bank guarantee"),
        "13": _("Renting of safes"),
        "14": _("Handling costs instalment credit"),
        "15": _("Night safe"),
        "16": _("Bank confirmation to revisor or accountant"),
        "17": _("Charge for safe custody"),
        "18": _("Trade information"),
        "19": _("Special charge for safe custody"),
        "20": _("Drawing up a certificate"),
        "21": _("Pay-packet charges"),
        "22": _("Management/custody"),
        "23": _("Research costs"),
        "24": _("Participation in and management of interest refund system"),
        "25": _("Renting of direct debit box"),
        "26": _("Travel insurance premium"),
        "27": _("Subscription fee"),
        "29": _("Information charges"),
        "31": _("Writ service fee"),
        "33": _("Miscellaneous fees and commissions"),
        "35": _("Costs"),
        "37": _("Access right to database"),
        "39": _("Surety fee"),
        "41": _("Research costs"),
        "43": _("Printing of forms"),
        "45": _("Documentary credit charges"),
        "47": _("Charging fees for transactions"),
        "49": _("Cancellation or correction"),
        "99": _("Cancellation or correction"),
        }],
}

transaction_categories = {
    "000": _("Net amount"),
    "001": _("Interest received"),
    "002": _("Interest paid"),
    "003": _("Credit commission"),
    "004": _("Postage"),
    "005": _("Renting of letterbox"),
    "006": _("Various fees/commissions"),
    "007": _("Access right to database"),
    "008": _("Information charges"),
    "009": _("Travelling expenses"),
    "010": _("Writ service fee"),
    "011": _("VAT"),
    "012": _("Exchange commission"),
    "013": _("Payment commission"),
    "014": _("Collection commission"),
    "015": _("Correspondent charges"),
    "016": _("BLIW/IBLC dues"),
    "017": _("Research costs"),
    "018": _("Tental guarantee charges"),
    "019": _("Tax on physical delivery"),
    "020": _("Costs of physical delivery"),
    "021": _("Costs for drawing up a bank cheque"),
    "022": _("Priority costs"),
    "023": _("Exercising fee"),
    "024": _("Growth premium"),
    "025": _("Individual entry for exchange charges"),
    "026": _("Handling commission"),
    "027": _("Charges for unpaid bills"),
    "028": _("Fidelity premium"),
    "029": _("Protest charges"),
    "030": _("Account insurance"),
    "031": _("Charges foreign cheque"),
    "032": _("Drawing up a circular cheque"),
    "033": _("Charges for a foreign bill"),
    "034": _("Reinvestment fee"),
    "035": _("Charges foreign documentary bill"),
    "036": _("Costs relating to a refused cheque"),
    "037": _("Commission for handling charges"),
    "039": _("Telecommunications"),
    "041": _("Credit card costs"),
    "042": _("Payment card costs"),
    "043": _("Insurance costs"),
    "045": _("Handling costs"),
    "047": _("Charges extension bill"),
    "049": _("Fiscal stamps/stamp duty"),
    "050": _("Capital term investment"),
    "051": _("Withholding tax"),
    "052": _("Residence state tax"),
    "053": _("Printing of forms"),
    "055": _("Repayment loan or credit capital"),
    "057": _("Interest subsidy"),
    "058": _("Capital premium"),
    "059": _("Default interest"),
    "061": _("Charging fees for transactions"),
    "063": _("Rounding differences"),
    "065": _("Interest payment advice"),
    "066": _("Fixed loan advance - reimbursement"),
    "067": _("Fixed loan advance - extension"),
    "068": _("Countervalue of an entry"),
    "069": _("Forward arbitrage contracts : sum to be supplied by customer"),
    "070": _("Forward arbitrage contracts : sum to be supplied by bank"),
    "071": _("Fixed loan advance - availability"),
    "072": _("Countervalue of commission to third party"),
    "073": _("Costs of ATM abroad"),
    "074": _("Mailing costs"),
    "100": _("Gross amount"),
    "200": _("Overall documentary credit charges"),
    "201": _("Advice notice commission"),
    "202": _("Advising commission | Additional advising commission"),
    "203": _("Confirmation fee | Additional confirmation fee | Commitment fee | Flat fee | Confirmation reservation commission | Additional reservation commission"),
    "204": _("Amendment fee"),
    "205": _("Documentary payment commission | Document commission | Drawdown fee | Negotiation fee"),
    "206": _("Surety fee/payment under reserve"),
    "207": _("Non-conformity fee"),
    "208": _("Commitment fee deferred payment"),
    "209": _("Transfer commission"),
    "210": _("Commitment fee"),
    "211": _("Credit arrangement fee | Additional credit arrangement fee"),
    "212": _("Warehousing fee"),
    "213": _("Financing fee"),
    "214": _("Issue commission (delivery order)"),
    "400": _("Acceptance fee"),
    "401": _("Visa charges"),
    "402": _("Certification costs"),
    "403": _("Minimum discount rate"),
    "404": _("Discount commission"),
    "405": _("Bill guarantee commission"),
    "406": _("Collection charges"),
    "407": _("Costs Article 45"),
    "408": _("Cover commission"),
    "409": _("Safe deposit charges"),
    "410": _("Reclamation charges"),
    "411": _("Fixed collection charge"),
    "412": _("Advice of expiry charges"),
    "413": _("Acceptance charges"),
    "414": _("Regularisation charges"),
    "415": _("Surety fee"),
    "416": _("Charges for the deposit of security"),
    "418": _("Endorsement commission"),
    "419": _("Bank service fee"),
    "420": _("Retention charges"),
    "425": _("Foreign broker's commission"),
    "426": _("Belgian broker's commission"),
    "427": _("Belgian Stock Exchange tax"),
    "428": _("Interest accrued"),
    "429": _("Foreign Stock Exchange tax"),
    "430": _("Recovery of foreign tax"),
    "431": _("Delivery of a copy"),
}


def rmspaces(s):
    return " ".join(s.split())



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
