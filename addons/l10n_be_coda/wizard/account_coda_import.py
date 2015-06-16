# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2012 Noviat nv/sa (www.noviat.be). All rights reserved.

import time
import re

from openerp import models, tools, _
from openerp.exceptions import UserError

class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    def _check_coda(self, data_file):
        # Matches the first 24 characters of a CODA file, as defined by the febelfin specifications
        return re.match('0{5}\d{9}05[ D] +', data_file) != None

    def _parse_file(self, data_file):
        if not self._check_coda(data_file):
            return super(AccountBankStatementImport, self)._parse_file(data_file)

        def rmspaces(s):
            return " ".join(s.split())

        recordlist = unicode(data_file, 'windows-1252', 'strict').split('\n')
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
                    raise UserError(_('Error') + ' R001: ' + _('CODA V%s statements are not supported, please contact your bank') % statement['version'])
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
                        raise UserError(_('Error') + ' R1001: ' + _('Foreign bank accounts with BBAN structure are not supported '))
                    elif line[1] == '2':    # Belgian bank account IBAN structure
                        statement['acc_number'] = rmspaces(line[5:21])
                        statement['currency'] = rmspaces(line[39:42])
                    elif line[1] == '3':    # foreign bank account IBAN structure
                        raise UserError(_('Error') + ' R1002: ' + _('Foreign bank accounts with IBAN structure are not supported '))
                    else:  # Something else, not supported
                        raise UserError(_('Error') + ' R1003: ' + _('Unsupported bank account structure '))
                statement['description'] = rmspaces(line[90:125])
                statement['balance_start'] = float(rmspaces(line[43:58])) / 1000
                if line[42] == '1':  # 1 = Debit, the starting balance is negative
                    statement['balance_start'] = - statement['balance_start']
                statement['balance_start_date'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[58:64]), '%d%m%y'))
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
                    statementLine['transactionDate'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[47:53]), '%d%m%y'))
                    statementLine['transaction_family'] = rmspaces(line[54:56])
                    statementLine['transaction_code'] = rmspaces(line[56:58])
                    statementLine['transaction_category'] = rmspaces(line[58:61])
                    if line[61] == '1':
                        #Structured communication
                        statementLine['communication_struct'] = True
                        statementLine['communication_type'] = line[62:65]
                        statementLine['communication'] = '+++' + line[65:68] + '/' + line[68:72] + '/' + line[72:77] + '+++'
                    else:
                        #Non-structured communication
                        statementLine['communication_struct'] = False
                        statementLine['communication'] = rmspaces(line[62:115])
                    statementLine['entryDate'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[115:121]), '%d%m%y'))
                    statementLine['type'] = 'normal'
                    statementLine['globalisation'] = int(line[124])
                    if statementLine['globalisation'] > 0:
                        if statementLine['globalisation'] in statement['globalisation_stack']:
                            statement['globalisation_stack'].remove(statementLine['globalisation'])
                        else:
                            statementLine['type'] = 'globalisation'
                            statement['globalisation_stack'].append(statementLine['globalisation'])
                            globalisation_comm[statementLine['ref_move']] = statementLine['communication']
                    if not statementLine.get('communication'):
                        statementLine['communication'] = globalisation_comm.get(statementLine['ref_move'], '')
                    statement['lines'].append(statementLine)
                elif line[1] == '2':
                    if statement['lines'][-1]['ref'][0:4] != line[2:6]:
                        raise UserError(_('Error') + 'R2004: ' + _('CODA parsing error on movement data record 2.2, seq nr %s! Please report this issue via your Odoo support channel.') % line[2:10])
                    statement['lines'][-1]['communication'] += rmspaces(line[10:63])
                    statement['lines'][-1]['payment_reference'] = rmspaces(line[63:98])
                    statement['lines'][-1]['counterparty_bic'] = rmspaces(line[98:109])
                elif line[1] == '3':
                    if statement['lines'][-1]['ref'][0:4] != line[2:6]:
                        raise UserError(_('Error') + 'R2005: ' + _('CODA parsing error on movement data record 2.3, seq nr %s! Please report this issue via your Odoo support channel.') % line[2:10])
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
                        statement['lines'][-1]['communication'] += rmspaces(line[82:125])
                else:
                    # movement data record 2.x (x != 1,2,3)
                    raise UserError(_('Error') + 'R2006: ' + _('\nMovement data records of type 2.%s are not supported ') % line[1])
            elif line[0] == '3':
                if line[1] == '1':
                    infoLine = {}
                    infoLine['entryDate'] = statement['lines'][-1]['entryDate']
                    infoLine['type'] = 'information'
                    infoLine['sequence'] = len(statement['lines']) + 1
                    infoLine['ref'] = rmspaces(line[2:10])
                    infoLine['transactionRef'] = rmspaces(line[10:31])
                    infoLine['transaction_family'] = rmspaces(line[32:34])
                    infoLine['transaction_code'] = rmspaces(line[34:36])
                    infoLine['transaction_category'] = rmspaces(line[36:39])
                    infoLine['communication'] = rmspaces(line[40:113])
                    statement['lines'].append(infoLine)
                elif line[1] == '2':
                    if infoLine['ref'] != rmspaces(line[2:10]):
                        raise UserError(_('Error') + 'R3004: ' + _('CODA parsing error on information data record 3.2, seq nr %s! Please report this issue via your Odoo support channel.') % line[2:10])
                    statement['lines'][-1]['communication'] += rmspaces(line[10:100])
                elif line[1] == '3':
                    if infoLine['ref'] != rmspaces(line[2:10]):
                        raise UserError(_('Error') + 'R3005: ' + _('CODA parsing error on information data record 3.3, seq nr %s! Please report this issue via your Odoo support channel.') % line[2:10])
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
        for i, statement in enumerate(statements):
            statement['coda_note'] = ''
            statement_line = []
            statement_data = {
                'name': statement['paperSeqNumber'],
                'date': statement['date'],
                'balance_start': statement['balance_start'],
                'balance_end_real': statement['balance_end_real'],
            }
            for line in statement['lines']:
                if line['type'] == 'information':
                    statement['coda_note'] = "\n".join([statement['coda_note'], line['type'].title() + ' with Ref. ' + str(line['ref']), 'Date: ' + str(line['entryDate']), 'Communication: ' + line['communication'], ''])
                elif line['type'] == 'communication':
                    statement['coda_note'] = "\n".join([statement['coda_note'], line['type'].title() + ' with Ref. ' + str(line['ref']), 'Ref: ', 'Communication: ' + line['communication'], ''])
                elif line['type'] == 'normal':
                    note = []
                    if line.get('counterpartyName'):
                        note.append(_('Counter Party') + ': ' + line['counterpartyName'])
                    else:
                        line['counterpartyName'] = False
                    if line.get('counterpartyNumber'):
                        try:
                            if int(line['counterpartyNumber']) == 0:
                                line['counterpartyNumber'] = False
                        except:
                            pass
                        if line['counterpartyNumber']:
                            note.append(_('Counter Party Account') + ': ' + line['counterpartyNumber'])
                    else:
                        line['counterpartyNumber'] = False

                    if line.get('counterpartyAddress'):
                        note.append(_('Counter Party Address') + ': ' + line['counterpartyAddress'])
                    structured_com = False
                    if line['communication_struct'] and 'communication_type' in line and line['communication_type'] == '101':
                        structured_com = line['communication']
                    if line.get('communication', ''):
                        note.append(_('Communication') + ': ' + line['communication'])
                    line_data = {
                        'name': structured_com or (line.get('communication', '') != '' and line['communication'] or '/'),
                        'note': "\n".join(note),
                        'date': line['entryDate'],
                        'amount': line['amount'],
                        'account_number': line.get('counterpartyNumber', None),
                        'partner_name': line['counterpartyName'],
                        'ref': line['ref'],
                        'sequence': line['sequence'],
                        'unique_import_id': str(statement['codaSeqNumber']) + '-' + str(statement['date']) + '-' + str(line['ref']),
                    }
                    statement_line.append(line_data)
            if statement['coda_note'] != '':
                statement_data.update({'coda_note': statement['coda_note']})
            statement_data.update({'transactions': statement_line})
            ret_statements.append(statement_data)
        currency_code = statement['currency']
        acc_number = statements[0] and statements[0]['acc_number'] or False
        return currency_code, acc_number, ret_statements
