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
                raise osv.except_osv(_('Error!'), _('Wizard in incorrect state. Please hit the Cancel button!'))
                return {}
        recordlist = unicode(base64.decodestring(codafile), 'windows-1252', 'strict').split('\n')
        statements = []
        for line in recordlist:
            if not line:
                continue
            elif line[0] == '0':
                #Begin of a new Bank statement
                statement = {}
                statements.append(statement)
                statement['error'] = False
                statement['errors'] = []
                statement['version'] = line[127]
                if statement['version'] not in ['1', '2']:
                    statement['error'] = True
                    statement['errors'].append(('R0001', _('CODA V%s statements are not supported, please contact your bank!') % statement['version']))
                    continue
                statement['lines'] = []
                statement['date'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[5:11]), '%d%m%y'))
                statement['separateApplication'] = rmspaces(line[83:88])
            elif not statement['error']:
                if line[0] == '1':
                    #Statement details
                    if statement['version'] == '1':
                        statement['accountNumber'] = rmspaces(line[5:17])
                        statement['currency'] = rmspaces(line[18:21])
                    elif statement['version'] == '2':
                        if line[1] == '0':  # Belgian bank account BBAN structure
                            statement['accountNumber'] = rmspaces(line[5:17])
                            statement['currency'] = rmspaces(line[18:21])
                        elif line[1] == '1':  # foreign bank account BBAN structure
                            statement['error'] = True
                            statement['errors'].append(('R1001', _('Foreign bank accounts with BBAN structure are not supported !')))
                            continue
                        elif line[1] == '2':    # Belgian bank account IBAN structure
                            statement['accountNumber'] = rmspaces(line[5:21])
                            statement['currency'] = rmspaces(line[39:42])
                        elif line[1] == '3':    # foreign bank account IBAN structure
                            statement['error'] = True
                            statement['errors'].append(('R1002', _('Foreign bank accounts with IBAN structure are not supported !')))
                            continue
                        else:  # Something else, not supported
                            statement['error'] = True
                            statement['errors'].append(('R1003', _('\nUnsupported bank account structure !')))
                            continue
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
                        if statementLine['sequence'] == 1:
                            main_move_stack = [statementLine]
                            glob_lvl_stack = [0]  # initialise globalisation stack
                        elif statementLine['ref_move_detail'] == '0000':
                            glob_lvl_stack = [0]  # re-initialise globalisation stack
                        statementLine['transactionRef'] = rmspaces(line[10:31])
                        statementLine['debit'] = line[31]  # 0 = Credit, 1 = Debit
                        statementLine['amount'] = float(rmspaces(line[32:47])) / 1000
                        if statementLine['debit'] == '1':
                            statementLine['amount'] = - statementLine['amount']
                        statementLine['transactionType'] = line[53]
                        #TODO Handling severals transactions types
                        statementLine['transactionDate'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[47:53]), '%d%m%y'))
                        statementLine['transactionFamily'] = rmspaces(line[54:56])
                        #TODO Handling severals transactions Family
                        statementLine['transactionCode'] = rmspaces(line[56:58])
                        #TODO Handling severals transactions code
                        statementLine['transactionCategory'] = rmspaces(line[58:61])
                        #TODO Handling severals transactions category
                        statementLine['communication'] = rmspaces(line[65:115])
                        #TODO Handling structured communication
                        statementLine['entryDate'] = rmspaces(line[115:121])

                        glob_lvl_flag = int(line[124])
                        if glob_lvl_flag > 0:
                            if glob_lvl_stack[-1] == glob_lvl_flag:
                                statementLine['glob_lvl_flag'] = glob_lvl_flag
                                statementLine['amount'] = statementLine['amount']
                                glob_lvl_stack.pop()
                            else:
                                glob_lvl_stack.append(glob_lvl_flag)
                                statementLine['type'] = 'globalisation'
                                statementLine['glob_lvl_flag'] = glob_lvl_flag
                                statementLine['globalisation_amount'] = statementLine['amount']
                                del statementLine['amount']

                        # The 'globalisation' concept can also be implemented without the globalisation level flag.
                        # This is e.g. used by Europabank to give the details of Card Payments.
                        if statementLine['ref_move'] == main_move_stack[-1]['ref_move']:
                            if statementLine['ref_move_detail'] == '9999':
                                statement['error'] = True
                                statement['errors'].append(('R1003', _('\nUnsupported bank account structure !')))
                                continue
                            elif statementLine['ref_move_detail'] != '0000':
                                if glob_lvl_stack[-1] == 0:
                                    # promote associated move record into a globalisation
                                    glob_lvl_flag = 1
                                    glob_lvl_stack.append(glob_lvl_flag)
                                    main_st_line_seq = main_move_stack[-1]['sequence']
                                    to_promote = statement['lines'][main_st_line_seq]
                                    if not main_move_stack[-1].get('detail_cnt'):
                                        to_promote.update({
                                           'type': 'globalisation',
                                           'glob_lvl_flag': glob_lvl_flag,
                                           'globalisation_amount': main_move_stack[-1]['amount'],
                                           'amount': False,
                                           'account_id': 0,
                                           })
                                        main_move_stack[-1]['promoted'] = True
                                if not main_move_stack[-1].get('detail_cnt'):
                                    main_move_stack[-1]['detail_cnt'] = 1
                                else:
                                    main_move_stack[-1]['detail_cnt'] += 1

                        statement['lines'].append(statementLine)

                        if statementLine['ref_move'] != main_move_stack[-1]['ref_move']:
                            if main_move_stack[-1].get('detail_cnt') and main_move_stack[-1].get('promoted'):
                                # add closing globalisation level on previous detail record in order to correctly close
                                # moves that have been 'promoted' to globalisation
                                closeglobalise = statement['lines'][len(statement['lines']) - 1]
                                closeglobalise.update({
                                        'glob_lvl_flag': main_move_stack[-1]['glob_lvl_flag'],
                                        })
                            else:
                                # demote record with globalisation code from 'globalisation' to 'general' when no detail records
                                # the same logic is repeated on the New Balance Record ('8 Record') in order to cope with CODA files
                                # containing a single 2.1 record that needs to be 'demoted'.
                                if main_move_stack[-1]['type'] == 'globalisation' and not main_move_stack[-1].get('detail_cnt'):
                                    # demote record with globalisation code from 'globalisation' to 'general' when no detail records
                                    main_st_line_seq = main_move_stack[-1]['sequence']
                                    to_demote = statement['lines'][main_st_line_seq]
                                    to_demote.update({
                                        'type': 'general',
                                        'glob_lvl_flag': 0,
                                        'globalisation_amount': False,
                                        'amount': main_move_stack[-1]['globalisation_amount'],
                                        })
                            main_move_stack.pop()
                            main_move_stack.append(statementLine)
                    elif line[1] == '2':
                        if statement['lines'][-1]['ref'][0:4] != line[2:6]:
                            statement['error'] = True
                            statement['errors'].append(('R2004', _('CODA parsing error on movement data record 2.2, seq nr %s! Please report this issue via your OpenERP support channel.') % line[2:10]))
                            continue
                        statement['lines'][-1]['communication'] += rmspaces(line[10:63])
                        statement['lines'][-1]['payment_reference'] = rmspaces(line[63:98])
                        statement['lines'][-1]['counterparty_bic'] = rmspaces(line[98:109])
                    elif line[1] == '3':
                        if statement['lines'][-1]['ref'][0:4] != line[2:6]:
                            statement['error'] = True
                            statement['errors'].append(('R2004', _('CODA parsing error on movement data record 2.2, seq nr %s! Please report this issue via your OpenERP support channel.') % line[2:10]))
                            continue
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
                        statement['error'] = True
                        statement['errors'].append(('R2009', _('\nMovement data records of type 2.%s are not supported !') % line[1]))
                elif line[0] == '3':
                    if line[1] == '1':
                        infoLine = {}
                        infoLine['entryDate'] = statement['lines'][-1]['entryDate']
                        infoLine['type'] = 'information'
                        infoLine['sequence'] = len(statement['lines']) + 1
                        infoLine['ref'] = rmspaces(line[2:10])
                        infoLine['transactionRef'] = rmspaces(line[10:31])
                        infoLine['transactionType'] = line[31]
                        infoLine['transactionFamily'] = rmspaces(line[32:34])
                        infoLine['transactionCode'] = rmspaces(line[34:36])
                        infoLine['transactioncategory'] = rmspaces(line[36:39])
                        infoLine['communication'] = rmspaces(line[40:113])
                        statement['lines'].append(infoLine)
                    elif line[1] == '2':
                        if statement['lines'][-1]['ref'] != rmspaces(line[2:10]):
                            statement['error'] = True
                            statement['errors'].append(('R3004', _('CODA parsing error on information data record 3.2, seq nr %s! Please report this issue via your OpenERP support channel.') % line[2:10]))
                            continue
                        statement['lines'][-1]['communication'] += rmspaces(line[10:100])
                    elif line[1] == '3':
                        if statement['lines'][-1]['ref'] != rmspaces(line[2:10]):
                            statement['error'] = True
                            statement['errors'].append(('R3005', _('CODA parsing error on information data record 3.3, seq nr %s! Please report this issue via your OpenERP support channel.') % line[2:10]))
                            continue
                        statement['lines'][-1]['communication'] += rmspaces(line[10:100])
                    elif line[0] == '4':
                        comm_line = {}
                        comm_line['type'] = 'communication'
                        comm_line['sequence'] = len(statement['lines']) + 1
                        comm_line['ref'] = rmspaces(line[2:10])
                        comm_line['communication'] = rmspaces(line[32:112])
                        statement['lines'].append(comm_line)
                elif line[0] == '8':
                    # new balance record
                    last_transaction = main_move_stack[-1]
                    if last_transaction['type'] == 'globalisation' and not last_transaction.get('detail_cnt'):
                        # demote record with globalisation code from 'globalisation' to 'general' when no detail records
                        main_st_line_seq = main_move_stack[-1]['sequence']
                        to_demote = statement['lines'][main_st_line_seq]
                        to_demote.update({
                            'type': 'general',
                            'glob_lvl_flag': 0,
                            'globalisation_amount': False,
                            'amount': main_move_stack[-1]['globalisation_amount'],
                            })
                        # add closing globalisation level on previous detail record in order to correctly close
                        # moves that have been 'promoted' to globalisation
                        if main_move_stack[-1].get('detail_cnt') and main_move_stack[-1].get('promoted'):
                            closeglobalise = statement['lines'][-1]
                            closeglobalise.update({
                                    'glob_lvl_flag': main_move_stack[-1]['glob_lvl_flag'],
                                    })
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
                        statement['error'] = True
                        statement['errors'].append(('R0002', _("The CODA Statement New Balance date doesn't fall within a defined Accounting Period! Please create the Accounting Period for date %s.") % statement['balance_end_realDate']))
                        continue
                    statement['period_id'] = period_id[0]
                elif line[0] == '9':
                    statement['balanceMin'] = float(rmspaces(line[22:37])) / 1000
                    statement['balancePlus'] = float(rmspaces(line[37:52])) / 1000
                    if not statement['balance_end_real']:
                        statement['balance_end_real'] = statement['balance_start'] + statement['balancePlus'] - statement['balanceMin']
        for i, statement in enumerate(statements):
            print '---STATEMENT #' + str(i) + '---'
            print statement
            if not statement['error']:
                data = {
                    'name': '[' + statement['date'] + ']' + statement['description'],
                    'date': statement['date'],
                    'journal_id': 18,
                    'period_id': statement['period_id'],
                    'balance_start': statement['balance_start'],
                    'balance_end_real': statement['balance_end_real'],
                    'account_id': 1
                }
                self.pool.get('account.bank.statement').create(cr, uid, data, context=context)

account_coda_import()


def rmspaces(s):
    return " ".join(s.split())

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
