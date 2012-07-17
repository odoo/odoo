# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    
#    Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.
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

import time
import base64
from osv import fields,osv
from tools.translate import _
import logging
import re
from traceback import format_exception
from sys import exc_info
_logger = logging.getLogger(__name__)

class account_coda_import(osv.osv_memory):
    _name = 'account.coda.import'
    _description = 'Import CODA File'
    _columns = {
        'coda_data': fields.binary('CODA File', required=True),
        'coda_fname': fields.char('CODA Filename', size=128, required=True),
        'note':fields.text('Log'),
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
            data=self.browse(cr,uid,ids)[0]
            try:
                codafile = data.coda_data
                codafilename = data.coda_fname            
            except:
                raise osv.except_osv(_('Error!'), _('Wizard in incorrect state. Please hit the Cancel button!'))
                return {}

        currency_obj = self.pool.get('res.currency')    
        coda_bank_account_obj = self.pool.get('coda.bank.account')
        trans_type_obj = self.pool.get('account.coda.trans.type')
        trans_code_obj = self.pool.get('account.coda.trans.code')
        trans_category_obj = self.pool.get('account.coda.trans.category')
        comm_type_obj = self.pool.get('account.coda.comm.type')
        journal_obj = self.pool.get('account.journal')
        period_obj = self.pool.get('account.period')
        partner_bank_obj = self.pool.get('res.partner.bank')
        coda_obj = self.pool.get('account.coda')
        coda_st_obj = self.pool.get('coda.bank.statement')
        coda_st_line_obj = self.pool.get('coda.bank.statement.line')
        bank_st_obj = self.pool.get('account.bank.statement')
        bank_st_line_obj = self.pool.get('account.bank.statement.line')
        glob_obj = self.pool.get('account.bank.statement.line.global')
        inv_obj = self.pool.get('account.invoice')
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        voucher_obj = self.pool.get('account.voucher')
        voucher_line_obj = self.pool.get('account.voucher.line')
        seq_obj = self.pool.get('ir.sequence')
        mod_obj = self.pool.get('ir.model.data')

        coda_bank_table = coda_bank_account_obj.read(cr, uid, coda_bank_account_obj.search(cr, uid, []), context=context)
        for coda_bank in coda_bank_table:
            coda_bank.update({'journal_code': coda_bank['journal'] and journal_obj.browse(cr, uid, coda_bank['journal'][0], context=context).code or ''})
            coda_bank.update({'iban': partner_bank_obj.browse(cr, uid, coda_bank['bank_id'][0], context=context).iban})
            coda_bank.update({'acc_number': partner_bank_obj.browse(cr, uid, coda_bank['bank_id'][0], context=context).acc_number})
            coda_bank.update({'currency_name': currency_obj.browse(cr, uid, coda_bank['currency'][0], context=context).name})            
        trans_type_table = trans_type_obj.read(cr, uid, trans_type_obj.search(cr, uid, []), context=context)
        trans_code_table = trans_code_obj.read(cr, uid, trans_code_obj.search(cr, uid, []), context=context)
        trans_category_table = trans_category_obj.read(cr, uid, trans_category_obj.search(cr, uid, []), context=context)
        comm_type_table = comm_type_obj.read(cr, uid, comm_type_obj.search(cr, uid, []), context=context)

        err_string = ''
        err_code = None
        err_log = ''
        coda_statements = []
        recordlist = unicode(base64.decodestring(codafile), 'windows-1252', 'strict').split('\n')
        
        for line in recordlist:
            
            if not line:
                pass
            elif line[0] == '0':
                # start of a new statement within the CODA file
                coda_statement = {}
                coda_parsing_note = ''
                coda_statement_lines = {}
                st_line_seq = 0
                glob_lvl_stack = [0]
                # header data
                coda_statement['currency'] = 'EUR'   # default currency                
                coda_statement['version'] = line[127]
                coda_version = line[127]
                if coda_version not in ['1','2']:
                    err_string = _('\nCODA V%s statements are not supported, please contact your bank!') % coda_version
                    err_code = 'R0001'
                    if batch:
                        return (err_code, err_string)
                    raise osv.except_osv(_('Data Error!'), err_string)
                coda_statement['coda_statement_lines'] = {}
                coda_statement['date'] = str2date(line[5:11])
                period_id = period_obj.search(cr , uid, [('date_start' ,'<=', coda_statement['date']), ('date_stop','>=',coda_statement['date'])])
                if not period_id:
                    err_string = _("\nThe CODA creation date doesn't fall within a defined Accounting Period!" \
                          "\nPlease create the Accounting Period for date %s.") % coda_statement['date']
                    err_code = 'R0002'
                    if batch:
                        return (err_code, err_string)
                    raise osv.except_osv(_('Data Error!'), err_string)
                coda_statement['period_id'] = period_id[0]
                coda_statement['state'] = 'draft'
        
                coda_id = coda_obj.search(cr, uid,[
                    ('name', '=', codafilename),
                    ('coda_creation_date', '=', coda_statement['date']),
                    ])
                if coda_id:
                    err_string = _("\nCODA File with Filename '%s' and Creation Date '%s' has already been imported !") \
                        % (codafilename, coda_statement['date'])
                    err_code = 'W0001'
                    if batch:
                        return (err_code, err_string)
                    raise osv.except_osv(_('Warning !'), err_string)
                
            elif line[0] == '1':
                if coda_version == '1':
                    coda_statement['acc_number'] = line[5:17]
                    if line[18:21].strip():
                        coda_statement['currency'] = line[18:21]
                elif line[1] == '0':                                # Belgian bank account BBAN structure
                    coda_statement['acc_number'] = line[5:17]
                    coda_statement['currency'] = line[18:21]             
                elif line[1] == '1':    # foreign bank account BBAN structure
                    err_string = _('\nForeign bank accounts with BBAN structure are not supported !')
                    err_code = 'R1001'
                    if batch:
                        return (err_code, err_string)
                    raise osv.except_osv(_('Data Error!'), err_string)
                elif line[1] == '2':    # Belgian bank account IBAN structure
                    coda_statement['acc_number']=line[5:21] 
                    coda_statement['currency'] = line[39:42]
                elif line[1] == '3':    # foreign bank account IBAN structure
                    err_string = _('\nForeign bank accounts with IBAN structure are not supported !')
                    err_code = 'R1002'
                    if batch:
                        return (err_code, err_string)
                    raise osv.except_osv(_('Data Error!'), err_string)
                else:
                    err_string = _('\nUnsupported bank account structure !')
                    err_code = 'R1003'
                    if batch:
                        return (err_code, err_string)
                    raise osv.except_osv(_('Data Error!'), err_string)
                coda_statement['description'] = line[90:125].strip()
                cba_filter = lambda x: ((coda_statement['acc_number'] in (x['iban'] or '')) or (coda_statement['acc_number'] == x['acc_number'])) \
                    and (coda_statement['currency'] == x['currency_name']) and (coda_statement['description'] == (x['description1'] or x['description2'] or ''))
                coda_bank =  filter(cba_filter, coda_bank_table)
                if coda_bank:
                    coda_bank = coda_bank[0] 
                    coda_statement['type'] = coda_bank['state']
                    coda_statement['journal_id'] = coda_bank['journal'] and coda_bank['journal'][0]
                    coda_statement['currency_id'] = coda_bank['currency'][0]
                    coda_statement['coda_bank_account_id'] = coda_bank['id']                   
                    def_pay_acc = coda_bank['def_payable'][0]
                    def_rec_acc = coda_bank['def_receivable'][0]
                    awaiting_acc = coda_bank['awaiting_account'][0]
                    transfer_acc = coda_bank['transfer_account'][0]
                    find_bbacom = coda_bank['find_bbacom']
                    find_partner = coda_bank['find_partner']
                else:
                    err_string = _("\nNo matching CODA Bank Account Configuration record found !") + \
                        _("\nPlease check if the 'Bank Account Number', 'Currency' and 'Account Description' fields of your configuration record match with '%s', '%s' and '%s' !") \
                        % (coda_statement['acc_number'], coda_statement['currency'], coda_statement['description'])
                    err_code = 'R1004'
                    if batch:
                        return (err_code, err_string)
                    raise osv.except_osv(_('Data Error!'), err_string)
                bal_start = list2float(line[43:58])             # old balance data
                if line[42] == '1':    # 1= Debit
                    bal_start = - bal_start
                coda_statement['balance_start'] = bal_start            
                coda_statement['acc_holder'] = line[64:90]
                coda_statement['paper_seq_number'] = line[2:5]
                coda_statement['coda_seq_number'] = line[125:128]
                if coda_bank['coda_st_naming']:
                    coda_statement['name'] = coda_bank['coda_st_naming'] % {
                       'code': coda_bank['journal_code'] or '',                                                    
                       'year': time.strftime('%Y'),
                       'y': time.strftime('%y'),
                       'coda': line[125:128],
                       'paper': line[2:5],
                    }
                else:
                    coda_statement['name'] = '/'
                    
            elif line[0] == '2':
                # movement data record 2
                if line[1] == '1':
                    # movement data record 2.1
                    st_line = {}
                    st_line_seq = st_line_seq + 1
                    st_line['sequence'] = st_line_seq
                    st_line['type'] = 'general'
                    st_line['reconcile'] = False         
                    st_line['struct_comm_type'] = ''
                    st_line['struct_comm_type_desc'] = ''
                    st_line['struct_comm_101'] = ''
                    st_line['communication'] = ''
                    st_line['partner_id'] = 0
                    st_line['account_id'] = 0
                    st_line['counterparty_name'] = ''
                    st_line['counterparty_bic'] = ''                    
                    st_line['counterparty_number'] = ''
                    st_line['counterparty_currency'] = ''                    
                    st_line['glob_lvl_flag'] = False
                    st_line['globalisation_id'] = 0
                    st_line['globalisation_code'] = ''
                    st_line['globalisation_amount'] = False
                    st_line['amount'] = False
                          
                    st_line['ref'] = line[2:10]
                    st_line['trans_ref'] = line[10:31]
                    st_line_amt = list2float(line[32:47])
                    if line[31] == '1':    # 1=debit
                        st_line_amt = - st_line_amt
                    # processing of amount depending on globalisation code    
                    glob_lvl_flag = int(line[124])
                    if glob_lvl_flag > 0: 
                        if glob_lvl_stack[-1] == glob_lvl_flag: 
                            st_line['glob_lvl_flag'] = glob_lvl_flag                            
                            st_line['amount'] = st_line_amt
                            glob_lvl_stack.pop()
                        else:
                            glob_lvl_stack.append(glob_lvl_flag)
                            st_line['type'] = 'globalisation'
                            st_line['glob_lvl_flag'] = glob_lvl_flag
                            st_line['globalisation_amount'] = st_line_amt
                            st_line['account_id'] = None
                    else:
                        st_line['amount'] = st_line_amt
                    # positions 48-53 : Value date or 000000 if not known (DDMMYY)
                    st_line['val_date'] = str2date(line[47:53])
                    # positions 54-61 : transaction code
                    st_line['trans_type'] = line[53]
                    trans_type =  filter(lambda x: st_line['trans_type'] == x['type'], trans_type_table)
                    if not trans_type:
                        err_string = _('\nThe File contains an invalid CODA Transaction Type : %s!') % st_line['trans_type']
                        err_code = 'R2001'
                        if batch:
                            return (err_code, err_string)
                        raise osv.except_osv(_('Data Error!'), err_string)                    
                    st_line['trans_type_desc'] = trans_type[0]['description']                         
                    st_line['trans_family'] = line[54:56]
                    trans_family =  filter(lambda x: (x['type'] == 'family') and (st_line['trans_family'] == x['code']), trans_code_table)
                    if not trans_family:
                        err_string = _('\nThe File contains an invalid CODA Transaction Family : %s!') % st_line['trans_family']                       
                        err_code = 'R2002'
                        if batch:
                            return (err_code, err_string)
                        raise osv.except_osv(_('Data Error!'), err_string)                    
                    st_line['trans_family_desc'] = trans_family[0]['description']
                    st_line['trans_code'] = line[56:58]
                    trans_code =  filter(lambda x: (x['type'] == 'code') and (st_line['trans_code'] == x['code']) and (trans_family[0]['id'] == x['parent_id'][0]), 
                        trans_code_table)
                    if trans_code:
                        st_line['trans_code_desc'] = trans_code[0]['description']
                    else:
                        st_line['trans_code_desc'] = _('Transaction Code unknown, please consult your bank.')
                    st_line['trans_category'] = line[58:61]
                    trans_category =  filter(lambda x: st_line['trans_category'] == x['category'], trans_category_table)
                    if trans_category:
                        st_line['trans_category_desc'] = trans_category[0]['description']
                    else:
                        st_line['trans_category_desc'] = _('Transaction Category unknown, please consult your bank.')       
                    # positions 61-115 : communication                
                    if line[61] == '1':
                        st_line['struct_comm_type'] = line[62:65]
                        comm_type =  filter(lambda x: st_line['struct_comm_type'] == x['code'], comm_type_table)
                        if not comm_type:
                            err_string = _('\nThe File contains an invalid Structured Communication Type : %s!') % st_line['struct_comm_type']
                            err_code = 'R2003'
                            if batch:
                                return (err_code, err_string)
                            raise osv.except_osv(_('Data Error!'), err_string)                    
                        st_line['struct_comm_type_desc'] = comm_type[0]['description']
                        st_line['communication'] = st_line['name'] = line[65:115]
                        if st_line['struct_comm_type'] == '101':
                            bbacomm = line[65:77]   
                            st_line['struct_comm_101'] = st_line['name'] = '+++' + bbacomm[0:3] + '/' + bbacomm[3:7] + '/' + bbacomm[7:] + '+++'     
                    else:
                        st_line['communication'] = st_line['name'] = line[62:115]
                    st_line['entry_date'] = str2date(line[115:121])
                    # positions 122-124 not processed 
                    coda_statement_lines[st_line_seq] = st_line
                    coda_statement['coda_statement_lines'] = coda_statement_lines
                elif line[1] == '2':
                    # movement data record 2.2
                    if coda_statement['coda_statement_lines'][st_line_seq]['ref'] != line[2:10]:
                        err_string = _('\nCODA parsing error on movement data record 2.2, seq nr %s!'    \
                            '\nPlease report this issue via your OpenERP support channel.') % line[2:10]
                        err_code = 'R2004'
                        if batch:
                            return (err_code, err_string)
                        raise osv.except_osv(_('Error!'), err_string)                    
                    coda_statement['coda_statement_lines'][st_line_seq]['name'] += line[10:63]
                    coda_statement['coda_statement_lines'][st_line_seq]['communication'] += line[10:63]
                    coda_statement['coda_statement_lines'][st_line_seq]['counterparty_bic'] = line[98:109].strip()                    
                elif line[1] == '3':
                    # movement data record 2.3
                    if coda_statement['coda_statement_lines'][st_line_seq]['ref'] != line[2:10]:
                        err_string = _('\nCODA parsing error on movement data record 2.3, seq nr %s!'    \
                            '\nPlease report this issue via your OpenERP support channel.') % line[2:10]
                        err_code = 'R2005'
                        if batch:
                            return (err_code, err_string)
                        raise osv.except_osv(_('Error!'), err_string)                    
                    st_line = coda_statement_lines[st_line_seq]
                    if coda_version == '1':
                        counterparty_number = line[10:22]
                        counterparty_name = line[47:125].strip()
                        counterparty_currency = ''
                    else:
                        if line[22] == ' ':
                            counterparty_number = line[10:22]
                            counterparty_currency = line[23:26].strip()
                        else:
                            counterparty_number = line[10:44].strip()
                            counterparty_currency = line[44:47].strip()                           
                        counterparty_name = line[47:82].strip()
                        st_line['name'] += line[82:125]
                        st_line['communication'] += line[82:125]
                    st_line['counterparty_number'] = counterparty_number
                    st_line['counterparty_currency'] = counterparty_currency
                    st_line['counterparty_name'] = counterparty_name
                    if counterparty_currency not in [coda_bank['currency_name'], '']:
                        err_string = _('\nCODA parsing error on movement data record 2.3, seq nr %s!'    \
                            '\nPlease report this issue via your OpenERP support channel.') % line[2:10]                   
                        err_code = 'R2006'
                        if batch:
                            return (err_code, err_string)
                        raise osv.except_osv(_('Error!'), err_string)    

                    # partner matching and reconciliation 
                    if st_line['type'] == 'general':                    
                        match = False
                        bank_ids = False
                        # prepare reconciliation for bba scor
                        reference = st_line['struct_comm_101']
                        if reference and find_bbacom:
                            inv_ids = inv_obj.search(cr , uid, [('reference' ,'=', reference), ('reference_type' ,'=', 'bba')])
                            if inv_ids:
                                invoice = inv_obj.browse(cr, uid, inv_ids[0])
                                partner = invoice.partner_id
                                st_line['partner_id'] = partner.id
                                if invoice.type in ['in_invoice', 'in_refund']:
                                    st_line['account_id'] = partner.property_account_payable.id or def_pay_acc
                                    st_line['type'] = 'supplier'
                                else:
                                    st_line['account_id'] = partner.property_account_receivable.id or def_rec_acc
                                    st_line['type'] = 'customer'
                                if invoice.type in ['in_invoice', 'out_invoice']:                                             
                                    iml_ids = move_line_obj.search(cr, uid, [('move_id', '=', invoice.move_id.id), ('reconcile_id', '=', False), ('account_id.reconcile', '=', True)])
                                if iml_ids:
                                    st_line['reconcile'] = iml_ids[0]
                                match = True
                            else:
                                coda_parsing_note += _("\n    Bank Statement '%s' line '%s':" \
                                    "\n        There is no invoice matching the Structured Communication '%s'!" \
                                    "\n        Please verify and adjust the invoice and perform the import again or otherwise change the corresponding entry manually in the generated Bank Statement.") \
                                    % (coda_statement['name'], st_line['ref'], reference)
                        # lookup partner via counterparty_number
                        if not match and counterparty_number:
                            cba_filter = lambda x: ((counterparty_number in (x['iban'] or '')) or (counterparty_number == x['acc_number'])) \
                                and (x['state'] == 'normal')
                            transfer_account =  filter(cba_filter, coda_bank_table)
                            if transfer_account:
                                st_line['account_id'] = transfer_acc
                                match = True
                            elif find_partner:
                                bank_ids = partner_bank_obj.search(cr,uid,[('acc_number','=', counterparty_number)])
                        if not match and find_partner and bank_ids:
                            if len(bank_ids) > 1:
                                coda_parsing_note += _("\n    Bank Statement '%s' line '%s':" \
                                    "\n        No partner record assigned: There are multiple partners with the same Bank Account Number '%s'!" \
                                    "\n        Please correct the configuration and perform the import again or otherwise change the corresponding entry manually in the generated Bank Statement.") \
                                    % (coda_statement['name'], st_line['ref'], counterparty_number)
                            else:    
                                bank = partner_bank_obj.browse(cr, uid, bank_ids[0], context)
                                st_line['partner_id'] = bank.partner_id.id
                                match = True
                                if st_line['amount'] < 0:
                                    st_line['account_id'] = bank.partner_id.property_account_payable.id or def_pay_acc
                                    st_line['type'] = 'supplier'
                                else:
                                    st_line['account_id'] = bank.partner_id.property_account_receivable.id or def_rec_acc
                                    st_line['type'] = 'customer'
                        elif not match and find_partner:
                            if counterparty_number:
                                coda_parsing_note += _("\n    Bank Statement '%s' line '%s':" \
                                    "\n        The bank account '%s' is not defined for the partner '%s'!" \
                                    "\n        Please correct the configuration and perform the import again or otherwise change the corresponding entry manually in the generated Bank Statement.") \
                                    % (coda_statement['name'], st_line['ref'], 
                                    counterparty_number, counterparty_name)
                            else:
                                coda_parsing_note += _("\n    Bank Statement '%s' line '%s':" \
                                    "\n        No matching partner record found!" \
                                    "\n        Please adjust the corresponding entry manually in the generated Bank Statement.") \
                                    % (coda_statement['name'], st_line['ref']) 
                            st_line['account_id'] = awaiting_acc
                    # end of partner record lookup
                    coda_statement_lines[st_line_seq] = st_line
                    coda_statement['coda_statement_lines'] = coda_statement_lines
                else:
                    # movement data record 2.x (x <> 1,2,3)
                    err_string = _('\nMovement data records of type 2.%s are not supported !') % line[1]
                    err_code = 'R2007'
                    if batch:
                        return (err_code, err_string)
                    raise osv.except_osv(_('Data Error!'), err_string)    

            elif line[0] == '3':
                # information data record 3
                if line[1] == '1':
                    # information data record 3.1
                    info_line = {}
                    info_line['entry_date'] = st_line['entry_date']
                    info_line['type'] = 'information'
                    st_line_seq = st_line_seq + 1
                    info_line['sequence'] = st_line_seq
                    info_line['struct_comm_type'] = ''
                    info_line['struct_comm_type_desc'] = ''
                    info_line['communication'] = ''
                    info_line['ref'] = line[2:10]
                    info_line['trans_ref'] = line[10:31]
                    # positions 32-38 : transaction code
                    info_line['trans_type'] = line[31]
                    trans_type =  filter(lambda x: info_line['trans_type'] == x['type'], trans_type_table)
                    if not trans_type:
                        err_string = _('\nThe File contains an invalid CODA Transaction Type : %s!') % st_line['trans_type']
                        err_code = 'R3001'
                        if batch:
                            return (err_code, err_string)
                        raise osv.except_osv(_('Data Error!'), err_string)                    
                    info_line['trans_type_desc'] = trans_type[0]['description']                         
                    info_line['trans_family'] = line[32:34]
                    trans_family =  filter(lambda x: (x['type'] == 'family') and (info_line['trans_family'] == x['code']), trans_code_table)
                    if not trans_family:
                        err_string = _('\nThe File contains an invalid CODA Transaction Family : %s!') % st_line['trans_family']                       
                        err_code = 'R3002'
                        if batch:
                            return (err_code, err_string)
                        raise osv.except_osv(_('Data Error!'), err_string)                    
                    info_line['trans_family_desc'] = trans_family[0]['description']
                    info_line['trans_code'] = line[34:36]
                    trans_code =  filter(lambda x: (x['type'] == 'code') and (info_line['trans_code'] == x['code']) and (trans_family[0]['id'] == x['parent_id']), 
                        trans_code_table)
                    if trans_code:
                        info_line['trans_code_desc'] = trans_code[0]['description']
                    else:
                        info_line['trans_code_desc'] = _('Transaction Code unknown, please consult your bank.')
                    info_line['trans_category'] = line[36:39]
                    trans_category =  filter(lambda x: info_line['trans_category'] == x['category'], trans_category_table)
                    if trans_category:
                        info_line['trans_category_desc'] = trans_category[0]['description']
                    else:
                        info_line['trans_category_desc'] = _('Transaction Category unknown, please consult your bank.')       
                    # positions 40-113 : communication                
                    if line[39] == '1':
                        info_line['struct_comm_type'] = line[40:43]
                        comm_type = filter(lambda x: info_line['struct_comm_type'] == x['code'], comm_type_table)
                        if not comm_type:
                            err_string = _('\nThe File contains an invalid Structured Communication Type : %s!') % info_line['struct_comm_type']
                            err_code = 'R3003'
                            if batch:
                                return (err_code, err_string)
                            raise osv.except_osv(_('Data Error!'), err_string)
                        info_line['struct_comm_type_desc'] = comm_type[0]['description']
                        info_line['communication'] = info_line['name'] = line[43:113]
                    else:
                        info_line['communication'] = info_line['name'] = line[40:113]
                    # positions 114-128 not processed
                    coda_statement_lines[st_line_seq] = info_line
                    coda_statement['coda_statement_lines'] = coda_statement_lines
                elif line[1] == '2':
                    # information data record 3.2
                    if coda_statement['coda_statement_lines'][st_line_seq]['ref'] != line[2:10]:
                        err_string = _('\nCODA parsing error on information data record 3.2, seq nr %s!'    \
                            '\nPlease report this issue via your OpenERP support channel.') % line[2:10]
                        err_code = 'R3004'
                        if batch:
                            return (err_code, err_string)
                        raise osv.except_osv(_('Error!'), err_string)
                    coda_statement['coda_statement_lines'][st_line_seq]['name'] += line[10:115]                        
                    coda_statement['coda_statement_lines'][st_line_seq]['communication'] += line[10:115]
                elif line[1] == '3':
                    # information data record 3.3
                    if coda_statement['coda_statement_lines'][st_line_seq]['ref'] != line[2:10]:
                        err_string = _('\nCODA parsing error on information data record 3.3, seq nr %s!'    \
                            '\nPlease report this issue via your OpenERP support channel.') % line[2:10]
                        err_code = 'R3005'
                        if batch:
                            return (err_code, err_string)
                        raise osv.except_osv(_('Error!'), err_string)
                    coda_statement['coda_statement_lines'][st_line_seq]['name'] += line[10:100]
                    coda_statement['coda_statement_lines'][st_line_seq]['communication'] += line[10:100]
                   
            elif line[0] == '4':
                # free communication data record 4
                comm_line = {}
                comm_line['type'] = 'communication'
                st_line_seq = st_line_seq + 1
                comm_line['sequence'] = st_line_seq
                comm_line['ref'] = line[2:10]
                comm_line['communication'] = comm_line['name'] = line[32:112]
                coda_statement_lines[st_line_seq] = comm_line
                coda_statement['coda_statement_lines'] = coda_statement_lines
    
            elif line[0] == '8':
                # new balance record
                bal_end = list2float(line[42:57])
                if line[41] == '1':    # 1=Debit
                    bal_end = - bal_end
                coda_statement['balance_end_real'] = bal_end
    
            elif line[0] == '9':
                # footer record
                coda_statement['balance_min'] = list2float(line[22:37])  
                coda_statement['balance_plus'] = list2float(line[37:52])
                if not bal_end:
                    coda_statement['balance_end_real'] = coda_statement['balance_start'] + coda_statement['balance_plus'] - coda_statement['balance_min']
                if coda_parsing_note:                
                    coda_statement['coda_parsing_note'] = '\nStatement Line matching results:' + coda_parsing_note
                else:
                    coda_statement['coda_parsing_note'] = ''
                coda_statements.append(coda_statement)
        #end for

        err_string = ''
        err_code = ''        
        coda_id = 0
        coda_note = ''
        line_note = ''
        
        try:
            coda_id = coda_obj.create(cr, uid,{
                'name' : codafilename,
                'coda_data': codafile,
                'coda_creation_date' : coda_statement['date'],
                'date': fields.date.context_today(self, cr, uid, context=context),
                'user_id': uid,
                })
            context.update({'coda_id': coda_id})
    
        except osv.except_osv, e:
            cr.rollback()
            err_string = _('\nApplication Error : ') + str(e)
        except Exception, e:
            cr.rollback()
            err_string = _('\nSystem Error : ') + str(e)
        except :
            cr.rollback()
            err_string = _('\nUnknown Error : ') + str(e)
        if err_string:
            err_code = 'G0001'
            if batch:
                return (err_code, err_string)
            raise osv.except_osv(_('CODA Import failed !'), err_string)

        nb_err = 0
        err_string = ''
        coda_st_ids = []
        bk_st_ids = []      
        
        for statement in coda_statements:
            
            # The CODA Statement info is written to two objects: 'coda.bank.statement' and 'account.bank.statement'

            try:
                
                coda_st_id = coda_st_obj.create(cr, uid, {
                    'name': statement['name'],
                    'type': statement['type'],
                    'coda_bank_account_id': statement['coda_bank_account_id'],
                    'currency': statement['currency_id'],                    
                    'journal_id': statement['journal_id'],
                    'coda_id': coda_id,
                    'date': statement['date'],
                    'period_id': statement['period_id'],
                    'balance_start': statement['balance_start'],
                    'balance_end_real': statement['balance_end_real'],
                    'state':'draft',
                })
                coda_st_ids.append(coda_st_id)

                if statement['type'] == 'normal':   
                    context.update({'ebanking_import': 1})
                    journal = journal_obj.browse(cr, uid, statement['journal_id'], context=context)
                    cr.execute('SELECT balance_end_real \
                        FROM account_bank_statement \
                        WHERE journal_id = %s and date < %s \
                        ORDER BY date DESC,id DESC LIMIT 1', (statement['journal_id'], statement['date']))
                    res = cr.fetchone()
                    balance_start_check = res and res[0]
                    if balance_start_check == None:
                        if journal.default_debit_account_id and (journal.default_credit_account_id == journal.default_debit_account_id):
                            balance_start_check = journal.default_debit_account_id.balance
                        else:
                            nb_err += 1 
                            err_string += _('\nConfiguration Error in journal %s!'    \
                                '\nPlease verify the Default Debit and Credit Account settings.') % journal.name
                            break
                    if balance_start_check <> statement['balance_start']:
                            nb_err += 1 
                            err_string += _('\nThe CODA Statement %s Starting Balance (%.2f) does not correspond with the previous Closing Balance (%.2f) in journal %s!')  \
                                % (statement['name'], statement['balance_start'], balance_start_check, journal.name)   
                            break                
                            
                    bk_st_id = bank_st_obj.create(cr, uid, {
                        'name': statement['name'],
                        'journal_id': statement['journal_id'],
                        'coda_statement_id': coda_st_id,
                        'date': statement['date'],
                        'period_id': statement['period_id'],
                        'balance_start': statement['balance_start'],
                        'balance_end_real': statement['balance_end_real'],
                        'state': 'draft',
                    })
                    bk_st_ids.append(bk_st_id)
                    coda_st_obj.write(cr, uid, [coda_st_id], {'statement_id': bk_st_id}, context=context)
    
                glob_id_stack = [(0, '', 0, '')]          # stack with tuples (glob_lvl_flag, glob_code, glob_id, glob_name)
                lines = statement['coda_statement_lines']
                st_line_seq = 0

                for x in lines:
                    line = lines[x]

                    # handling non-transactional records : line['type'] in ['information', 'communication']
                    
                    if line['type'] == 'information':

                        line['globalisation_id'] = glob_id_stack[-1][2]
                        line_note = _('Transaction Type' ': %s - %s'                \
                            '\nTransaction Family: %s - %s'                         \
                            '\nTransaction Code: %s - %s'                           \
                            '\nTransaction Category: %s - %s'                       \
                            '\nStructured Communication Type: %s - %s'              \
                            '\nCommunication: %s')                                  \
                            %(line['trans_type'], line['trans_type_desc'],
                              line['trans_family'], line['trans_family_desc'],
                              line['trans_code'], line['trans_code_desc'],
                              line['trans_category'], line['trans_category_desc'],
                              line['struct_comm_type'], line['struct_comm_type_desc'],
                              line['communication'])
    
                        coda_st_line_id = coda_st_line_obj.create(cr, uid, {
                                   'sequence': line['sequence'],
                                   'ref': line['ref'],                                           
                                   'name': line['name'].strip() or '/',
                                   'type' : 'information',               
                                   'date': line['entry_date'],                
                                   'statement_id': coda_st_id,
                                   'note': line_note,
                                   })
                            
                    elif line['type'] == 'communication':

                        line_note = _('Free Communication:\n %s')                  \
                            %(line['communication'])
    
                        coda_st_line_id = coda_st_line_obj.create(cr, uid, {
                                   'sequence': line['sequence'],
                                   'ref': line['ref'],                                                 
                                   'name': line['name'].strip() or '/',
                                   'type' : 'communication',
                                   'date': statement['date'],
                                   'statement_id': coda_st_id,
                                   'note': line_note,
                                   })

                    # handling transactional records, # line['type'] in ['globalisation', 'general', 'supplier', 'customer'] 

                    else:
                    
                        glob_lvl_flag = line['glob_lvl_flag']
                        if glob_lvl_flag: 
                            if glob_id_stack[-1][0] == glob_lvl_flag: 
                                line['globalisation_id'] = glob_id_stack[-1][2]
                                glob_id_stack.pop()
                            else:
                                glob_name = line['name'].strip() or '/'
                                glob_code = seq_obj.get(cr, uid, 'statement.line.global')
                                glob_id = glob_obj.create(cr, uid, {
                                    'code': glob_code,                                                                
                                    'name': glob_name,
                                    'type': 'coda',
                                    'parent_id': glob_id_stack[-1][2],
                                    'amount': line['globalisation_amount'],
                                })
                                line['globalisation_id'] = glob_id
                                glob_id_stack.append((glob_lvl_flag, glob_code, glob_id, glob_name))
    
                        line_note = _('Partner name: %s \nPartner Account Number: %s' \
                            '\nTransaction Type: %s - %s'                             \
                            '\nTransaction Family: %s - %s'                           \
                            '\nTransaction Code: %s - %s'                             \
                            '\nTransaction Category: %s - %s'                         \
                            '\nStructured Communication Type: %s - %s'                \
                            '\nCommunication: %s')                                    \
                            %(line['counterparty_name'], line['counterparty_number'],
                              line['trans_type'], line['trans_type_desc'],
                              line['trans_family'], line['trans_family_desc'],
                              line['trans_code'], line['trans_code_desc'],
                              line['trans_category'], line['trans_category_desc'],
                              line['struct_comm_type'], line['struct_comm_type_desc'],
                              line['communication'])
    
                        if line['type'] == 'globalisation':
                            
                            coda_st_line_id = coda_st_line_obj.create(cr, uid, {
                                   'sequence': line['sequence'],
                                   'ref': line['ref'],                                                  
                                   'name': line['name'].strip() or '/',
                                   'type' : 'globalisation',
                                   'val_date' : line['val_date'], 
                                   'date': line['entry_date'],
                                   'globalisation_level': line['glob_lvl_flag'],  
                                   'globalisation_amount': line['globalisation_amount'],                                                      
                                   'globalisation_id': line['globalisation_id'], 
                                   'partner_id': line['partner_id'] or 0,
                                   'account_id': line['account_id'],
                                   'statement_id': coda_st_id,
                                   'note': line_note,
                                   })

                        else:       # line['type'] in ['general', 'supplier', 'customer']                        

                            if glob_lvl_flag == 0: 
                                line['globalisation_id'] = glob_id_stack[-1][2]
                            if not line['account_id']:                               
                                    line['account_id'] = awaiting_acc
                                                                
                            coda_st_line_id = coda_st_line_obj.create(cr, uid, {
                                   'sequence': line['sequence'],
                                   'ref': line['ref'],                                                   
                                   'name': line['name'] or '/',
                                   'type' : line['type'],
                                   'val_date' : line['val_date'], 
                                   'date': line['entry_date'],
                                   'amount': line['amount'],
                                   'partner_id': line['partner_id'] or 0,
                                   'counterparty_name': line['counterparty_name'],
                                   'counterparty_bic': line['counterparty_bic'],                     
                                   'counterparty_number': line['counterparty_number'],   
                                   'counterparty_currency': line['counterparty_currency'],                                    
                                   'account_id': line['account_id'],
                                   'globalisation_level': line['glob_lvl_flag'],  
                                   'globalisation_id': line['globalisation_id'], 
                                   'statement_id': coda_st_id,
                                   'note': line_note,
                                   })

                            if statement['type'] == 'normal':
                                
                                st_line_seq += 1
                                voucher_id = False
                                line_name = line['name'].strip()
                                if not line_name:
                                    if line['globalisation_id']:
                                        line_name = glob_id_stack[-1][3]
                                    else:
                                        line_name = '/'

                                if line['reconcile']:
                                    voucher_vals = { 
                                        'type': line['type'] == 'supplier' and 'payment' or 'receipt',
                                        'name': line_name,
                                        'partner_id': line['partner_id'],
                                        'journal_id': statement['journal_id'],
                                        'account_id': journal.default_credit_account_id.id,
                                        'company_id': journal.company_id.id,
                                        'currency_id': journal.company_id.currency_id.id,
                                        'date': line['entry_date'],
                                        'amount': abs(line['amount']),
                                        'period_id': statement['period_id'],
                                    }
                                    voucher_id = voucher_obj.create(cr, uid, voucher_vals, context=context)

                                    move_line = move_line_obj.browse(cr, uid, line['reconcile'], context=context)
                                    voucher_dict = voucher_obj.onchange_partner_id(cr, uid, [], 
                                        partner_id = line['partner_id'], 
                                        journal_id = statement['journal_id'], 
                                        price = abs(line['amount']), 
                                        currency_id = journal.company_id.currency_id.id, 
                                        ttype = line['type'] == 'supplier' and 'payment' or 'receipt',
                                        date = line['val_date'],
                                        context = context)
                                    #_logger.warning('voucher_dict = %s' % voucher_dict) 
                                    voucher_line_vals = False
                                    if voucher_dict['value']['line_ids']:
                                        for line_dict in voucher_dict['value']['line_ids']:
                                            if line_dict['move_line_id'] == move_line.id:
                                                voucher_line_vals = line_dict
                                    if voucher_line_vals:
                                        voucher_line_vals.update({
                                            'voucher_id': voucher_id,
                                            'amount': abs(line['amount']),
                                        })
                                        voucher_line_obj.create(cr, uid, voucher_line_vals, context=context)

                                bank_st_line_id = bank_st_line_obj.create(cr, uid, {
                                       'sequence': st_line_seq,
                                       'ref': line['ref'],                                                   
                                       'name': line_name,
                                       'type' : line['type'],
                                       'val_date' : line['val_date'], 
                                       'date': line['entry_date'],
                                       'amount': line['amount'],
                                       'partner_id': line['partner_id'] or 0,
                                       'counterparty_name': line['counterparty_name'],
                                       'counterparty_bic': line['counterparty_bic'],                     
                                       'counterparty_number': line['counterparty_number'],   
                                       'counterparty_currency': line['counterparty_currency'],                                                                           
                                       'account_id': line['account_id'],
                                       'globalisation_id': line['globalisation_id'], 
                                       'statement_id': bk_st_id,
                                       'voucher_id': voucher_id,
                                       'note': line_note,
                                        })   
                # end 'for x in lines'

                coda_st_obj.write(cr, uid, [coda_st_id], {}, context=context)           # calculate balance
                st_balance = coda_st_obj.read(cr, uid, coda_st_id, ['balance_end', 'balance_end_real'], context=context)
                if st_balance['balance_end'] <> st_balance['balance_end_real']:
                    err_string += _('\nIncorrect ending Balance in CODA Statement %s for Bank Account %s!')  \
                        % (statement['coda_seq_number'], (statement['acc_number'] + ' (' + statement['currency'] + ') - ' + statement['description']))
                    if statement['type'] == 'normal':
                        nb_err += 1
                        break
                    else:
                        statement['coda_parsing_note'] += '\n' + err_string
                              
                if statement['type'] == 'normal':                          
                    bank_st_obj.button_dummy(cr, uid, [bk_st_id], context=context)      # calculate balance   
                    journal_name = journal.name
                else:
                    journal_name = _('None')
                coda_note = coda_note +                                                 \
                    _('\n\nBank Journal: %s'                                            \
                    '\nCODA Version: %s'                                                \
                    '\nCODA Sequence Number: %s'                                        \
                    '\nPaper Statement Sequence Number: %s'                             \
                    '\nBank Account: %s'                                                \
                    '\nAccount Holder Name: %s'                                         \
                    '\nDate: %s, Starting Balance:  %.2f, Ending Balance: %.2f'         \
                    '%s')                                                               \
                    %(journal_name,
                      coda_version,
                      statement['coda_seq_number'],
                      statement['paper_seq_number'],
                      (statement['acc_number'] + ' (' + statement['currency'] + ') - ' + statement['description']),
                      statement['acc_holder'],
                      statement['date'], float(statement['balance_start']), float(statement['balance_end_real']),
                      statement['coda_parsing_note'])

            except osv.except_osv, e:
                cr.rollback()
                nb_err += 1
                err_string += _('\nError ! ') + str(e)
                tb = ''.join(format_exception(*exc_info()))
                _logger.error('Application Error while processing Statement %s\n%s' % (statement.get('name', '/'),tb))
            except Exception, e:
                cr.rollback()
                nb_err += 1
                err_string += _('\nSystem Error : ') + str(e)
                tb = ''.join(format_exception(*exc_info()))
                _logger.error('System Error while processing Statement %s\n%s' % (statement.get('name', '/'),tb))
            except :
                cr.rollback()
                nb_err += 1
                err_string = _('\nUnknown Error : ') + str(e)
                tb = ''.join(format_exception(*exc_info()))
                _logger.error('Unknown Error while processing Statement %s\n%s' % (statement.get('name', '/'),tb))

        # end 'for statement in coda_statements'
                          
        coda_note_header = _('CODA File is Imported  :')
        coda_note_footer = _('\n\nNumber of statements : ') + str(len(coda_st_ids))
        err_log = err_log + _('\nNumber of errors : ') + str(nb_err) + '\n'

        if not nb_err:
            note = coda_note_header + coda_note + coda_note_footer
            coda_obj.write(cr, uid,[coda_id],{'note': note })
            cr.commit()
            if batch:
                return None
        else:
            cr.rollback()
            if batch:
                err_code = 'G0002'
                return (err_code, err_string)
            raise osv.except_osv(_('CODA Import failed !'), err_string)
            
        context.update({ 'bk_st_ids': bk_st_ids})
        model_data_ids = mod_obj.search(cr, uid, [('model', '=', 'ir.ui.view'), ('name', '=', 'account_coda_import_result_view')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        self.write(cr, uid, ids, {'note': note}, context=context)
        
        return {
            'name': _('Import CODA File result'),
            'res_id': ids[0],
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.coda.import',
            'view_id': False,
            'target': 'new',
            'views': [(resource_id, 'form')],
            'context': context,
            'type': 'ir.actions.act_window',
        }

    def action_open_coda_statements(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        module, xml_id = 'account_coda', 'action_coda_bank_statements'
        res_model, res_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, module, xml_id)
        action = self.pool.get('ir.actions.act_window').read(cr, uid, res_id, context=context)
        domain = eval(action.get('domain') or '[]')
        domain += [('coda_id', '=', context.get('coda_id', False))]
        action.update({'domain': domain})
        return action

    def action_open_bank_statements(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        module, xml_id = 'account', 'action_bank_statement_tree'
        res_model, res_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, module, xml_id)
        action = self.pool.get('ir.actions.act_window').read(cr, uid, res_id, context=context)
        domain = eval(action.get('domain') or '[]')
        domain += [('id','in', context.get('bk_st_ids', False))]
        action.update({'domain': domain})
        return action
        
account_coda_import()

def str2date(date_str):
    return time.strftime('%Y-%m-%d', time.strptime(date_str,'%d%m%y'))

def str2float(str):
    try:
        return float(str)
    except:
        return 0.0

def list2float(lst):
            try:
                return str2float((lambda s : s[:-3] + '.' + s[-3:])(lst))
            except:
                return 0.0

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
