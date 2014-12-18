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
import time

from openerp.osv import osv
from openerp.tools.translate import _
from openerp import tools

import logging

_logger = logging.getLogger(__name__)

from openerp.addons.account_bank_statement_import import account_bank_statement_import as coda_ibs

coda_ibs.add_file_type(('coda', 'CODA'))

class account_bank_statement_import(osv.TransientModel):
    _inherit = "account.bank.statement.import"

    def process_coda(self, cr, uid, codafile=None, journal_id=False, context=None):
        if context is None:
            context = {}
        recordlist = unicode(base64.decodestring(codafile), 'windows-1252', 'strict').split('\n')
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
                    raise osv.except_osv(_('Error') + ' R001', _('CODA V%s statements are not supported, please contact your bank') % statement['version'])
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
                        raise osv.except_osv(_('Error') + ' R1001', _('Foreign bank accounts with BBAN structure are not supported '))
                    elif line[1] == '2':    # Belgian bank account IBAN structure
                        statement['acc_number'] = rmspaces(line[5:21])
                        statement['currency'] = rmspaces(line[39:42])
                    elif line[1] == '3':    # foreign bank account IBAN structure
                        raise osv.except_osv(_('Error') + ' R1002', _('Foreign bank accounts with IBAN structure are not supported '))
                    else:  # Something else, not supported
                        raise osv.except_osv(_('Error') + ' R1003', _('Unsupported bank account structure '))
                statement['journal_id'] = False
                statement['bank_account'] = False
                # Belgian Account Numbers are composed of 12 digits.
                # In OpenERP, the user can fill the bank number in any format: With or without IBan code, with or without spaces, with or without '-'
                # The two following sql requests handle those cases.
                if len(statement['acc_number']) >= 12:
                    # If the Account Number is >= 12 digits, it is mostlikely a Belgian Account Number (With or without IBAN).
                    # The following request try to find the Account Number using a 'like' operator.
                    # So, if the Account Number is stored with IBAN code, it can be found thanks to this.
                    cr.execute("select id from res_partner_bank where replace(replace(acc_number,' ',''),'-','') like %s", ('%' + statement['acc_number'] + '%',))
                else:
                    # This case is necessary to avoid cases like the Account Number in the CODA file is set to a single or few digits,
                    # and so a 'like' operator would return the first account number in the database which matches.
                    cr.execute("select id from res_partner_bank where replace(replace(acc_number,' ',''),'-','') = %s", (statement['acc_number'],))
                bank_ids = [id[0] for id in cr.fetchall()]
                # Filter bank accounts which are not allowed
                bank_ids = self.pool.get('res.partner.bank').search(cr, uid, [('id', 'in', bank_ids)])
                if bank_ids and len(bank_ids) > 0:
                    bank_accs = self.pool.get('res.partner.bank').browse(cr, uid, bank_ids)
                    for bank_acc in bank_accs:
                        if bank_acc.journal_id.id and ((bank_acc.journal_id.currency.id and bank_acc.journal_id.currency.name == statement['currency']) or (not bank_acc.journal_id.currency.id and bank_acc.journal_id.company_id.currency_id.name == statement['currency'])):
                            statement['journal_id'] = bank_acc.journal_id
                            statement['bank_account'] = bank_acc
                            break
                if not statement['bank_account']:
                    raise osv.except_osv(_('Error') + ' R1004', _("No matching Bank Account (with Account Journal) found.\n\nPlease set-up a Bank Account with as Account Number '%s' and as Currency '%s' and an Account Journal.") % (statement['acc_number'], statement['currency']))
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
                        statementLine['type'] = 'globalisation'
                        globalisation_comm[statementLine['ref_move']] = statementLine['communication']
                    if not statementLine.get('communication'):
                        statementLine['communication'] = globalisation_comm.get(statementLine['ref_move'], '')
                    statement['lines'].append(statementLine)
                elif line[1] == '2':
                    if statement['lines'][-1]['ref'][0:4] != line[2:6]:
                        raise osv.except_osv(_('Error') + 'R2004', _('CODA parsing error on movement data record 2.2, seq nr %s! Please report this issue via your Odoo support channel.') % line[2:10])
                    statement['lines'][-1]['communication'] += rmspaces(line[10:63])
                    statement['lines'][-1]['payment_reference'] = rmspaces(line[63:98])
                    statement['lines'][-1]['counterparty_bic'] = rmspaces(line[98:109])
                elif line[1] == '3':
                    if statement['lines'][-1]['ref'][0:4] != line[2:6]:
                        raise osv.except_osv(_('Error') + 'R2005', _('CODA parsing error on movement data record 2.3, seq nr %s! Please report this issue via your Odoo support channel.') % line[2:10])
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
                    raise osv.except_osv(_('Error') + 'R2006', _('\nMovement data records of type 2.%s are not supported ') % line[1])
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
                        raise osv.except_osv(_('Error') + 'R3004', _('CODA parsing error on information data record 3.2, seq nr %s! Please report this issue via your Odoo support channel.') % line[2:10])
                    statement['lines'][-1]['communication'] += rmspaces(line[10:100])
                elif line[1] == '3':
                    if infoLine['ref'] != rmspaces(line[2:10]):
                        raise osv.except_osv(_('Error') + 'R3005', _('CODA parsing error on information data record 3.3, seq nr %s! Please report this issue via your Odoo support channel.') % line[2:10])
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
                if statement['balance_end_realDate']:
                    period_id = self.pool.get('account.period').search(cr, uid, [('company_id', '=', statement['journal_id'].company_id.id), ('date_start', '<=', statement['balance_end_realDate']), ('date_stop', '>=', statement['balance_end_realDate'])])
                else:
                    period_id = self.pool.get('account.period').search(cr, uid, [('company_id', '=', statement['journal_id'].company_id.id), ('date_start', '<=', statement['date']), ('date_stop', '>=', statement['date'])])
                if not period_id and len(period_id) == 0:
                    raise osv.except_osv(_('Error') + 'R0002', _("The CODA Statement New Balance date doesn't fall within a defined Accounting Period! Please create the Accounting Period for date %s for the company %s.") % (statement['balance_end_realDate'], statement['journal_id'].company_id.name))
                statement['period_id'] = period_id[0]
            elif line[0] == '9':
                statement['balanceMin'] = float(rmspaces(line[22:37])) / 1000
                statement['balancePlus'] = float(rmspaces(line[37:52])) / 1000
                if not statement.get('balance_end_real'):
                    statement['balance_end_real'] = statement['balance_start'] + statement['balancePlus'] - statement['balanceMin']
        for i, statement in enumerate(statements):
            statement['coda_note'] = ''
            statement_line = []
            balance_start_check_date = (len(statement['lines']) > 0 and statement['lines'][0]['entryDate']) or statement['date']
            cr.execute('SELECT balance_end_real \
                FROM account_bank_statement \
                WHERE journal_id = %s and date <= %s \
                ORDER BY date DESC,id DESC LIMIT 1', (statement['journal_id'].id, balance_start_check_date))
            res = cr.fetchone()
            balance_start_check = res and res[0]
            if balance_start_check is None:
                if statement['journal_id'].default_debit_account_id and (statement['journal_id'].default_credit_account_id == statement['journal_id'].default_debit_account_id):
                    balance_start_check = statement['journal_id'].default_debit_account_id.balance
                else:
                    raise osv.except_osv(_('Error'), _("Configuration Error in journal %s!\nPlease verify the Default Debit and Credit Account settings.") % statement['journal_id'].name)
            if balance_start_check != statement['balance_start']:
                statement['coda_note'] = _("The CODA Statement %s Starting Balance (%.2f) does not correspond with the previous Closing Balance (%.2f) in journal %s!") % (statement['description'] + ' #' + statement['paperSeqNumber'], statement['balance_start'], balance_start_check, statement['journal_id'].name)
            if not(statement.get('period_id')):
                raise osv.except_osv(_('Error') + ' R3006', _(' No transactions or no period in coda file !'))
            statement_data = {
                'name': statement['paperSeqNumber'],
                'date': statement['date'],
                'journal_id': statement['journal_id'].id,
                'period_id': statement['period_id'],
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
                    if 'counterpartyName' in line and line['counterpartyName'] != '':
                        note.append(_('Counter Party') + ': ' + line['counterpartyName'])
                    else:
                        line['counterpartyName'] = False
                    if 'counterpartyNumber' in line and line['counterpartyNumber'] != '':
                        try:
                            if int(line['counterpartyNumber']) == 0:
                                line['counterpartyNumber'] = False
                        except:
                            pass
                        if line['counterpartyNumber']:
                            note.append(_('Counter Party Account') + ': ' + line['counterpartyNumber'])
                    else:
                        line['counterpartyNumber'] = False

                    if 'counterpartyAddress' in line and line['counterpartyAddress'] != '':
                        note.append(_('Counter Party Address') + ': ' + line['counterpartyAddress'])
                    structured_com = False
                    if line['communication_struct'] and 'communication_type' in line and line['communication_type'] == '101':
                        structured_com = line['communication']
                    bank_account_id = False
                    partner_id = False
                    if 'counterpartyNumber' in line and line['counterpartyNumber']:
                        bank_account_id, partner_id = self._detect_partner(cr, uid, str(line['counterpartyNumber']), identifying_field='acc_number', context=context)
                    if line.get('communication', ''):
                        note.append(_('Communication') + ': ' + line['communication'])
                    line_data = {
                        'name': structured_com or (line.get('communication', '') != '' and line['communication'] or '/'),
                        'note': "\n".join(note),
                        'date': line['entryDate'],
                        'amount': line['amount'],
                        'partner_id': partner_id,
                        'partner_name': line['counterpartyName'],
                        'ref': line['ref'],
                        'sequence': line['sequence'],
                        'bank_account_id': bank_account_id,
                    }
                    statement_line.append((0, 0, line_data))
            if statement['coda_note'] != '':
                statement_data.update({'coda_note': statement['coda_note']})
            statement_data.update({'journal_id': journal_id, 'line_ids': statement_line})
        return [statement_data]

def rmspaces(s):
    return " ".join(s.split())



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
