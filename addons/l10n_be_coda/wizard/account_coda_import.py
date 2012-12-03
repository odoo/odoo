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

import time
import base64
from osv import fields, osv
from tools.translate import _
import netsvc
import re
from traceback import format_exception
from sys import exc_info
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

    def _check_account_payment(self, cr, uid, context=None):
        res = self.pool.get('ir.module.module').search(cr, uid, [('name', '=', 'account_payment'), ('state', '=', 'installed')])
        return res and True or False

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
        move_line_obj = self.pool.get('account.move.line')
        voucher_obj = self.pool.get('account.voucher')
        seq_obj = self.pool.get('ir.sequence')
        mod_obj = self.pool.get('ir.model.data')
        account_mapping_obj = self.pool.get('coda.account.mapping.rule')

        if self._check_account_payment(cr, uid):
            payment_line_obj = self.pool.get('payment.line')
        else:
            payment_line_obj = False

        wf_service = netsvc.LocalService('workflow')

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
        digits = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')

        for line in recordlist:

            if not line:
                pass
            elif line[0] == '0':
                # start of a new statement within the CODA file
                coda_statement = {}
                coda_parsing_note = ''
                coda_statement_lines = {}
                st_line_seq = 0
                # header data
                coda_statement['currency'] = 'EUR'   # default currency
                coda_statement['version'] = line[127]
                coda_version = line[127]
                if coda_version not in ['1', '2']:
                    err_string = _('\nCODA V%s statements are not supported, please contact your bank!') % coda_version
                    err_code = 'R0001'
                    if batch:
                        return (err_code, err_string)
                    raise osv.except_osv(_('Data Error!'), err_string)
                coda_statement['coda_statement_lines'] = {}
                coda_statement['date'] = str2date(line[5:11])
                coda_statement['coda_creation_date'] = str2date(line[5:11])
                coda_statement['separate_application'] = line[83:88]
                coda_statement['first_transaction_date'] = False
                coda_statement['state'] = 'draft'

                coda_id = coda_obj.search(cr, uid, [
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
                    coda_statement['acc_number'] = line[5:21]
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
                cba_filter = lambda x: (coda_statement['acc_number'] in _get_acc_numbers(x['acc_number'])) \
                    and (coda_statement['currency'] == x['currency_name']) and (coda_statement['description'] in [x['description1'] or '', x['description2'] or ''])
                coda_bank = filter(cba_filter, coda_bank_table)
                if coda_bank:
                    coda_bank = coda_bank[0]
                    coda_statement['type'] = coda_bank['state']
                    coda_statement['journal_id'] = coda_bank['journal'] and coda_bank['journal'][0]
                    coda_statement['currency_id'] = coda_bank['currency'][0]
                    coda_statement['coda_bank_account_id'] = coda_bank['id']
                    coda_statement['account_mapping_ids'] = coda_bank['account_mapping_ids']
                    coda_statement['coda_bank_params'] = coda_bank
                    awaiting_acc = coda_bank['awaiting_account'][0]
                    transfer_acc = coda_bank['transfer_account'][0]
                    find_payment = coda_bank['find_payment']
                    find_bbacom = coda_bank['find_bbacom']
                    find_inv_number = coda_bank['find_inv_number']
                    find_partner = coda_bank['find_partner']
                    update_partner = coda_bank['update_partner']
                    coda_statement['balance_start_enforce'] = coda_bank['balance_start_enforce']
                    coda_statement['discard_dup'] = coda_bank['discard_dup']
                    company_id = coda_bank['company_id'][0]
                    company_bank_ids = partner_bank_obj.search(cr, uid, [('company_id', '=', company_id)])
                    company_bank_accounts = partner_bank_obj.read(cr, uid, company_bank_ids, ['acc_number'])
                    company_bank_accounts = [x['acc_number'].replace(' ', '') for x in company_bank_accounts]
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
                coda_statement['old_balance_date'] = str2date(line[58:64])
                coda_statement['acc_holder'] = line[64:90]
                coda_statement['paper_ob_seq_number'] = line[2:5]
                coda_statement['coda_seq_number'] = line[125:128]

            elif line[0] == '2':
                # movement data record 2

                if line[1] == '1':
                    # movement data record 2.1
                    st_line = {}
                    st_line_seq = st_line_seq + 1
                    st_line['sequence'] = st_line_seq
                    st_line['type'] = 'general'
                    st_line['reconcile'] = False
                    st_line['trans_family'] = False
                    st_line['struct_comm_type'] = ''
                    st_line['struct_comm_type_id'] = 0
                    st_line['struct_comm_type_desc'] = ''
                    st_line['struct_comm_bba'] = ''
                    st_line['communication'] = ''
                    st_line['payment_reference'] = ''
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
                    st_line['ref_move'] = line[2:6]
                    st_line['ref_move_detail'] = line[6:10]

                    if st_line_seq == 1:
                        main_move_stack = [st_line]     # initialise main_move_stack (used to link 2.1 detail records to 2.1 main record
                        glob_lvl_stack = [0]            # initialise globalisation stack
                    elif st_line['ref_move_detail'] == '0000':
                        glob_lvl_stack = [0]            # re-initialise globalisation stack

                    st_line['trans_ref'] = line[10:31]
                    st_line_amt = list2float(line[32:47])
                    if line[31] == '1':    # 1=debit
                        st_line_amt = - st_line_amt

                    st_line['trans_type'] = line[53]
                    trans_type = filter(lambda x: st_line['trans_type'] == x['type'], trans_type_table)
                    if not trans_type:
                        err_string = _('\nThe File contains an invalid CODA Transaction Type : %s!') % st_line['trans_type']
                        err_code = 'R2001'
                        if batch:
                            return (err_code, err_string)
                        raise osv.except_osv(_('Data Error!'), err_string)
                    st_line['trans_type_id'] = trans_type[0]['id']
                    st_line['trans_type_desc'] = trans_type[0]['description']

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
                    else:
                        st_line['amount'] = st_line_amt

                    # The 'globalisation' concept can also be implemented without the globalisation level flag.
                    # This is e.g. used by Europabank to give the details of Card Payments.
                    if st_line['ref_move'] == main_move_stack[-1]['ref_move']:
                        if st_line['ref_move_detail'] == '9999':
                            # Current CODA parsing logic doesn't support > 9999 detail lines
                            err_string = _('\nTransaction Detail Limit reached!')
                            err_code = 'R2010'
                            if batch:
                                return (err_code, err_string)
                            raise osv.except_osv(_('Data Error!'), err_string)
                        elif st_line['ref_move_detail'] != '0000':
                            if glob_lvl_stack[-1] == 0:
                                # promote associated move record into a globalisation
                                glob_lvl_flag = 1
                                glob_lvl_stack.append(glob_lvl_flag)
                                main_st_line_seq = main_move_stack[-1]['sequence']
                                to_promote = coda_statement['coda_statement_lines'][main_st_line_seq]
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

                    # positions 48-53 : Valuta date or 000000 if not known (DDMMYY)
                    st_line['val_date'] = str2date(line[47:53])
                    # positions 54-61 : transaction code
                    st_line['trans_family'] = line[54:56]
                    trans_family = filter(lambda x: (x['type'] == 'family') and (st_line['trans_family'] == x['code']), trans_code_table)
                    if not trans_family:
                        err_string = _('\nThe File contains an invalid CODA Transaction Family : %s!') % st_line['trans_family']
                        err_code = 'R2002'
                        if batch:
                            return (err_code, err_string)
                        raise osv.except_osv(_('Data Error!'), err_string)
                    st_line['trans_family_id'] = trans_family[0]['id']
                    st_line['trans_family_desc'] = trans_family[0]['description']
                    st_line['trans_code'] = line[56:58]
                    trans_code = filter(lambda x: (x['type'] == 'code') and (st_line['trans_code'] == x['code']) and (trans_family[0]['id'] == x['parent_id'][0]),
                        trans_code_table)
                    if trans_code:
                        st_line['trans_code_id'] = trans_code[0]['id']
                        st_line['trans_code_desc'] = trans_code[0]['description']
                    else:
                        st_line['trans_code_id'] = None
                        st_line['trans_code_desc'] = _('Transaction Code unknown, please consult your bank.')
                    st_line['trans_category'] = line[58:61]
                    trans_category = filter(lambda x: st_line['trans_category'] == x['category'], trans_category_table)
                    if trans_category:
                        st_line['trans_category_id'] = trans_category[0]['id']
                        st_line['trans_category_desc'] = trans_category[0]['description']
                    else:
                        st_line['trans_category_id'] = None
                        st_line['trans_category_desc'] = _('Transaction Category unknown, please consult your bank.')
                    # positions 61-115 : communication
                    if line[61] == '1':
                        st_line['struct_comm_type'] = line[62:65]
                        comm_type = filter(lambda x: st_line['struct_comm_type'] == x['code'], comm_type_table)
                        if not comm_type:
                            err_string = _('\nThe File contains an invalid Structured Communication Type : %s!') % st_line['struct_comm_type']
                            err_code = 'R2003'
                            if batch:
                                return (err_code, err_string)
                            raise osv.except_osv(_('Data Error!'), err_string)
                        st_line['struct_comm_type_id'] = comm_type[0]['id']
                        st_line['struct_comm_type_desc'] = comm_type[0]['description']
                        st_line['communication'] = st_line['name'] = line[65:115]
                        if st_line['struct_comm_type'] in ['101', '102']:
                            bbacomm = line[65:77]
                            st_line['struct_comm_bba'] = st_line['name'] = '+++' + bbacomm[0:3] + '/' + bbacomm[3:7] + '/' + bbacomm[7:] + '+++'
                    else:
                        st_line['communication'] = st_line['name'] = line[62:115]
                    st_line['entry_date'] = str2date(line[115:121])
                    if st_line['sequence'] == 1:
                        coda_statement['first_transaction_date'] = st_line['entry_date']
                    # positions 122-124 not processed
                    coda_statement_lines[st_line_seq] = st_line  # store transaction

                    if st_line['ref_move'] != main_move_stack[-1]['ref_move']:
                        if main_move_stack[-1].get('detail_cnt') and main_move_stack[-1].get('promoted'):
                            # add closing globalisation level on previous detail record in order to correctly close
                            # moves that have been 'promoted' to globalisation
                            closeglobalise = coda_statement['coda_statement_lines'][st_line_seq - 1]
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
                                to_demote = coda_statement['coda_statement_lines'][main_st_line_seq]
                                to_demote.update({
                                    'type': 'general',
                                    'glob_lvl_flag': 0,
                                    'globalisation_amount': False,
                                    'amount': main_move_stack[-1]['globalisation_amount'],
                                    })
                        main_move_stack.pop()
                        main_move_stack.append(st_line)
                    coda_statement['coda_statement_lines'] = coda_statement_lines

                elif line[1] == '2':
                    # movement data record 2.2
                    if coda_statement['coda_statement_lines'][st_line_seq]['ref'][0:4] != line[2:6]:
                        err_string = _('\nCODA parsing error on movement data record 2.2, seq nr %s!'    \
                            '\nPlease report this issue via your OpenERP support channel.') % line[2:10]
                        err_code = 'R2004'
                        if batch:
                            return (err_code, err_string)
                        raise osv.except_osv(_('Error!'), err_string)
                    coda_statement['coda_statement_lines'][st_line_seq]['name'] += line[10:63]
                    coda_statement['coda_statement_lines'][st_line_seq]['communication'] += line[10:63]
                    coda_statement['coda_statement_lines'][st_line_seq]['payment_reference'] = line[63:98].strip()
                    coda_statement['coda_statement_lines'][st_line_seq]['counterparty_bic'] = line[98:109].strip()

                elif line[1] == '3':
                    # movement data record 2.3
                    if coda_statement['coda_statement_lines'][st_line_seq]['ref'][0:4] != line[2:6]:
                        err_string = _('\nCODA parsing error on movement data record 2.3, seq nr %s!'    \
                            '\nPlease report this issue via your OpenERP support channel.') % line[2:10]
                        err_code = 'R2005'
                        if batch:
                            return (err_code, err_string)
                        raise osv.except_osv(_('Error!'), err_string)
                    st_line = coda_statement_lines[st_line_seq]
                    if coda_version == '1':
                        counterparty_number = line[10:22].strip()
                        counterparty_name = line[47:125].strip()
                        counterparty_currency = ''
                    else:
                        if line[22] == ' ':
                            counterparty_number = line[10:22].strip()
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
                    """
                    TO DO:

                    replace code infra by check on flag 128 and copy info in Notes Field.

                    if counterparty_currency not in [coda_bank['currency_name'], '']:
                        err_string = _('\nCODA parsing error on movement data record 2.3, seq nr %s!'    \
                            '\nPlease report this issue via your OpenERP support channel.') % line[2:10]
                        err_code = 'R2006'
                        if batch:
                            return (err_code, err_string)
                        raise osv.except_osv(_('Error!'), err_string)
                    """

                    # invoice matching and reconciliation
                    if st_line['type'] == 'general':
                        match = False
                        payment_reference_match = False
                        inv_ids = None
                        partner_bank_ids = False

                        # check payment reference in bank statement line against payment order lines
                        payment_reference = st_line['payment_reference']
                        if payment_reference and find_payment and st_line['amount'] < 0:
                            payline_ids = payment_line_obj and payment_line_obj.search(cr, uid, [('name', '=', payment_reference)])
                            if payline_ids:
                                if len(payline_ids) == 1:
                                    payline = payment_line_obj.browse(cr, uid, payline_ids[0])
                                    match = True
                                    payment_reference_match = True
                                    st_line['partner_id'] = payline.partner_id.id
                                    if payline.move_line_id:
                                        st_line['reconcile'] = payline.move_line_id.id
                                        st_line['account_id'] = payline.move_line_id.account_id.id
                                    if payline._get_ml_inv_ref:
                                        inv_type = payline.ml_inv_ref.type
                                        st_line['type'] = inv_type == 'in_invoice' and 'supplier' or 'customer'
                                    else:
                                        st_line['type'] = 'general'
                                else:
                                    err_string = _('\nThe CODA parsing detected a payment reference ambiguity while processing movement data record 2.3, seq nr %s!'    \
                                        '\nPlease check your Payment Gateway configuration or contact your OpenERP support channel.') % line[2:10]
                                    err_code = 'R2007'
                                    if batch:
                                        return (err_code, err_string)
                                    raise osv.except_osv(_('Error!'), err_string)

                        # check bba scor in bank statement line against open invoices
                        if st_line['struct_comm_bba'] and find_bbacom:
                            if st_line['amount'] > 0:
                                domain = [('type', 'in', ['out_invoice', 'in_refund'])]
                            else:
                                domain = [('type', 'in', ['in_invoice', 'out_refund'])]
                            inv_ids = inv_obj.search(cr, uid,
                                    domain + [('state', '=', 'open'), ('reference', '=', st_line['struct_comm_bba']), ('reference_type', '=', 'bba')])
                            if not inv_ids:
                                coda_parsing_note += _("\n    Bank Statement '%%(name)s' line '%s':" \
                                    "\n        There is no invoice matching the Structured Communication '%s'!" \
                                    "\n        Please verify and adjust the invoice and perform the import again or otherwise change the corresponding entry manually in the generated Bank Statement.") \
                                    % (st_line['ref'], st_line['struct_comm_bba'])
                            elif len(inv_ids) == 1:
                                match = True
                            elif len(inv_ids) > 1:
                                coda_parsing_note += _("\n    Bank Statement '%%(name)s' line '%s':" \
                                    "\n        There are multiple invoices matching the Structured Communication '%s'!" \
                                    "\n        A manual reconciliation is required.") \
                                    % (st_line['ref'], st_line['struct_comm_bba'])

                        # use free comm in bank statement line for lookup against open invoices
                        if not match and find_bbacom:
                            # extract possible bba scor from free form communication and try to find matching invoice
                            free_comm_digits = re.sub('\D', '', st_line['communication'] or '')
                            select = "SELECT id FROM (SELECT id, type, state, amount_total, number, reference_type, reference, " \
                                     "'%s'::text AS free_comm_digits FROM account_invoice) sq " \
                                     "WHERE state = 'open' AND reference_type = 'bba' " \
                                     "AND free_comm_digits LIKE '%%'||regexp_replace(reference, '\\\D', '', 'g')||'%%'" \
                                     % (free_comm_digits)
                            if st_line['amount'] > 0:
                                select2 = " AND type IN ('out_invoice', 'in_refund')"
                            else:
                                select2 = " AND type IN ('in_invoice', 'out_refund')"
                            cr.execute(select + select2)
                            res = cr.fetchall()
                            if res:
                                inv_ids = [x[0] for x in res]
                                if len(inv_ids) == 1:
                                    match = True
                        if not match and st_line['communication'] and find_inv_number:
                            # check matching invoice number in free form communication combined with matching amount
                            free_comm = repl_special(st_line['communication'].strip())
                            amount_fmt = '%.' + str(digits) + 'f'
                            if st_line['amount'] > 0:
                                amount_rounded = amount_fmt % round(st_line['amount'], digits)
                            else:
                                amount_rounded = amount_fmt % round(-st_line['amount'], digits)
                            select = "SELECT id FROM (SELECT id, type, state, amount_total, number, reference_type, reference, " \
                                     "'%s'::text AS free_comm FROM account_invoice) sq " \
                                     "WHERE state = 'open' AND amount_total = %s" \
                                     % (free_comm, amount_rounded)
                            # 'out_invoice', 'in_refund'
                            if st_line['amount'] > 0:
                                select2 = " AND type = 'out_invoice' AND free_comm ilike '%'||number||'%'"
                                cr.execute(select + select2)
                                res = cr.fetchall()
                                if res:
                                    inv_ids = [x[0] for x in res]
                                else:
                                    select2 = " AND type = 'in_refund' AND free_comm ilike '%'||reference||'%'"
                                    cr.execute(select + select2)
                                    res = cr.fetchall()
                                    if res:
                                        inv_ids = [x[0] for x in res]
                            # 'in_invoice', 'out_refund'
                            else:
                                select2 = " AND type = 'in_invoice' AND free_comm ilike '%'||reference||'%'"
                                cr.execute(select + select2)
                                res = cr.fetchall()
                                if res:
                                    inv_ids = [x[0] for x in res]
                                else:
                                    select2 = " AND type = 'out_refund' AND free_comm ilike '%'||number||'%'"
                                    cr.execute(select + select2)
                                    res = cr.fetchall()
                                    if res:
                                        inv_ids = [x[0] for x in res]
                            if inv_ids:
                                if len(inv_ids) == 1:
                                    match = True
                                elif len(inv_ids) > 1:
                                    coda_parsing_note += _("\n    Bank Statement '%%(name)s' line '%s':" \
                                        "\n        There are multiple invoices matching the Invoice Amount and Reference." \
                                        "\n        A manual reconciliation is required.") \
                                        % (st_line['ref'])

                        if not payment_reference_match and match and inv_ids and len(inv_ids) == 1:
                            invoice = inv_obj.browse(cr, uid, inv_ids[0])
                            partner = invoice.partner_id
                            st_line['partner_id'] = partner.id
                            if invoice.type in ['in_invoice', 'in_refund']:
                                st_line['account_id'] = partner.property_account_payable.id
                                st_line['type'] = 'supplier'
                            else:
                                st_line['account_id'] = partner.property_account_receivable.id
                                st_line['type'] = 'customer'
                            iml_ids = move_line_obj.search(cr, uid, [('move_id', '=', invoice.move_id.id), ('reconcile_id', '=', False), ('account_id.reconcile', '=', True)])
                            if iml_ids:
                                st_line['reconcile'] = iml_ids[0]
                            else:
                                err_string = _('\nThe CODA parsing detected a database inconsistency while processing movement data record 2.3, seq nr %s!'    \
                                    '\nPlease report this issue via your OpenERP support channel.') % line[2:10]
                                err_code = 'R2008'
                                if batch:
                                    return (err_code, err_string)
                                raise osv.except_osv(_('Error!'), err_string)

                        # lookup partner via counterparty_number when invoice lookup failed
                        if not match and counterparty_number:
                            transfer_account = filter(lambda x: counterparty_number in x, company_bank_accounts)
                            if transfer_account:
                                st_line['account_id'] = transfer_acc
                                match = True
                            elif find_partner:
                                partner_bank_ids = partner_bank_obj.search(cr, uid, [('acc_number', '=', counterparty_number)])
                        if not match and find_partner and partner_bank_ids:
                            if len(partner_bank_ids) > 1:
                                coda_parsing_note += _("\n    Bank Statement '%%(name)s' line '%s':" \
                                    "\n        No partner record assigned: There are multiple partners with the same Bank Account Number '%s'!" \
                                    "\n        Please correct the configuration and perform the import again or otherwise change the corresponding entry manually in the generated Bank Statement.") \
                                    % (st_line['ref'], counterparty_number)
                            else:
                                partner_bank = partner_bank_obj.browse(cr, uid, partner_bank_ids[0], context)
                                st_line['partner_id'] = partner_bank.partner_id.id
                                match = True
                                if st_line['amount'] < 0:
                                    st_line['account_id'] = partner_bank.partner_id.property_account_payable.id
                                    st_line['type'] = 'supplier'
                                else:
                                    st_line['account_id'] = partner_bank.partner_id.property_account_receivable.id
                                    st_line['type'] = 'customer'
                        elif not match and find_partner:
                            if counterparty_number:
                                coda_parsing_note += _("\n    Bank Statement '%%(name)s' line '%s':" \
                                    "\n        The bank account '%s' is not defined for the partner '%s'!" \
                                    "\n        Please correct the configuration and perform the import again or otherwise change the corresponding entry manually in the generated Bank Statement.") \
                                    % (st_line['ref'], counterparty_number, counterparty_name)
                            else:
                                coda_parsing_note += _("\n    Bank Statement '%%(name)s' line '%s':" \
                                    "\n        No matching partner record found!" \
                                    "\n        Please adjust the corresponding entry manually in the generated Bank Statement.") \
                                    % (st_line['ref'])
                            st_line['account_id'] = awaiting_acc

                        # add bank account to partner record
                        if match and st_line['account_id'] != transfer_acc and counterparty_number and update_partner:
                            partner_bank_ids = partner_bank_obj.search(cr, uid, [('acc_number', '=', counterparty_number), ('partner_id', '=', st_line['partner_id'])], order='id')
                            if len(partner_bank_ids) > 1:
                                # clean up partner bank duplicates, keep most recently created
                                _logger.warn('Duplicate Bank Accounts for partner_id %s have been removed, ids = %s',
                                    st_line['partner_id'], partner_bank_ids[:-1])
                                partner_bank_obj.unlink(cr, uid, partner_bank_ids[:-1])
                            if not partner_bank_ids:
                                feedback = update_partner_bank(self, cr, uid, st_line['counterparty_bic'], counterparty_number, st_line['partner_id'], counterparty_name)
                                if feedback:
                                    coda_parsing_note += _("\n    Bank Statement '%%(name)s' line '%s':") % st_line['ref'] + feedback

                    coda_statement_lines[st_line_seq] = st_line
                    coda_statement['coda_statement_lines'] = coda_statement_lines
                    # end of processing movement data record 2.3

                else:
                    # movement data record 2.x (x <> 1,2,3)
                    err_string = _('\nMovement data records of type 2.%s are not supported !') % line[1]
                    err_code = 'R2009'
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
                    trans_type = filter(lambda x: info_line['trans_type'] == x['type'], trans_type_table)
                    if not trans_type:
                        err_string = _('\nThe File contains an invalid CODA Transaction Type : %s!') % st_line['trans_type']
                        err_code = 'R3001'
                        if batch:
                            return (err_code, err_string)
                        raise osv.except_osv(_('Data Error!'), err_string)
                    info_line['trans_type_desc'] = trans_type[0]['description']
                    info_line['trans_family'] = line[32:34]
                    trans_family = filter(lambda x: (x['type'] == 'family') and (info_line['trans_family'] == x['code']), trans_code_table)
                    if not trans_family:
                        err_string = _('\nThe File contains an invalid CODA Transaction Family : %s!') % st_line['trans_family']
                        err_code = 'R3002'
                        if batch:
                            return (err_code, err_string)
                        raise osv.except_osv(_('Data Error!'), err_string)
                    info_line['trans_family_desc'] = trans_family[0]['description']
                    info_line['trans_code'] = line[34:36]
                    trans_code = filter(lambda x: (x['type'] == 'code') and (info_line['trans_code'] == x['code']) and (trans_family[0]['id'] == x['parent_id'][0]),
                        trans_code_table)
                    if trans_code:
                        info_line['trans_code_desc'] = trans_code[0]['description']
                    else:
                        info_line['trans_code_desc'] = _('Transaction Code unknown, please consult your bank.')
                    info_line['trans_category'] = line[36:39]
                    trans_category = filter(lambda x: info_line['trans_category'] == x['category'], trans_category_table)
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
                last_transaction = main_move_stack[-1]
                if last_transaction['type'] == 'globalisation' and not last_transaction.get('detail_cnt'):
                    # demote record with globalisation code from 'globalisation' to 'general' when no detail records
                    main_st_line_seq = main_move_stack[-1]['sequence']
                    to_demote = coda_statement['coda_statement_lines'][main_st_line_seq]
                    to_demote.update({
                        'type': 'general',
                        'glob_lvl_flag': 0,
                        'globalisation_amount': False,
                        'amount': main_move_stack[-1]['globalisation_amount'],
                        })
                    # add closing globalisation level on previous detail record in order to correctly close
                    # moves that have been 'promoted' to globalisation
                    if main_move_stack[-1].get('detail_cnt') and main_move_stack[-1].get('promoted'):
                        closeglobalise = coda_statement['coda_statement_lines'][st_line_seq - 1]
                        closeglobalise.update({
                                'glob_lvl_flag': main_move_stack[-1]['glob_lvl_flag'],
                                })
                coda_statement['paper_nb_seq_number'] = line[1:4]
                bal_end = list2float(line[42:57])
                coda_statement['new_balance_date'] = str2date(line[57:63])
                if line[41] == '1':    # 1=Debit
                    bal_end = - bal_end
                coda_statement['balance_end_real'] = bal_end
                if coda_statement['new_balance_date']:
                    period_id = period_obj.search(cr, uid, [('date_start', '<=', coda_statement['new_balance_date']), ('date_stop', '>=', coda_statement['new_balance_date'])])
                else:
                    period_id = period_obj.search(cr, uid, [('date_start', '<=', coda_statement['date']), ('date_stop', '>=', coda_statement['date'])])
                if not period_id:
                    err_string = _("\nThe CODA Statement New Balance date doesn't fall within a defined Accounting Period!" \
                          "\nPlease create the Accounting Period for date %s.") % coda_statement['new_balance_date']
                    err_code = 'R0002'
                    if batch:
                        return (err_code, err_string)
                    raise osv.except_osv(_('Data Error!'), err_string)
                coda_statement['period_id'] = period_id[0]
                if coda_bank['coda_st_naming']:
                    coda_statement['name'] = coda_bank['coda_st_naming'] % {
                       'code': coda_bank['journal_code'] or '',
                       'year': coda_statement['new_balance_date'] and coda_statement['new_balance_date'][:4] or coda_statement['date'][:4],
                       'y': coda_statement['new_balance_date'] and coda_statement['new_balance_date'][2:4] or coda_statement['date'][2:4],
                       'coda': coda_statement['coda_seq_number'],
                       'paper_ob': coda_statement['paper_ob_seq_number'],
                       'paper': coda_statement['paper_nb_seq_number'],
                    }
                else:
                    coda_statement['name'] = '/'

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
            coda_id = coda_obj.create(cr, uid, {
                'name': codafilename,
                'coda_data': codafile,
                'coda_creation_date': coda_statement['date'],
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
        except:
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
                normal2info = False
                lines = statement['coda_statement_lines']
                if not statement['first_transaction_date']:
                    normal2info = True  # don't create a bank statement for CODA's without transactions
                else:
                    line_vals = [x for x in lines.itervalues()]
                    transactions = filter(lambda x: (x['type'] in ['globalisation', 'general', 'supplier', 'customer']) and x['amount'], line_vals)
                    if not transactions:
                        normal2info = True  # don't create a bank statement for CODA's without transactions
                if normal2info:
                    statement['type'] = 'info'  # don't create a bank statement for CODA's without transactions
                    statement['coda_parsing_note'] += _("\n\nThe CODA Statement %s does not contain transactions, hence no Bank Statement has been created." \
                        "\nSelect the 'CODA Bank Statement' to check the contents of %s.") \
                        % (statement['name'], statement['name'])

                coda_st_id = coda_st_obj.create(cr, uid, {
                    'name': statement['name'],
                    'type': statement['type'],
                    'coda_bank_account_id': statement['coda_bank_account_id'],
                    'currency': statement['currency_id'],
                    'journal_id': statement['journal_id'],
                    'coda_id': coda_id,
                    'date': statement['date'],
                    'coda_creation_date': statement['coda_creation_date'],
                    'period_id': statement['period_id'],
                    'old_balance_date': statement['old_balance_date'],
                    'new_balance_date': statement['new_balance_date'],
                    'balance_start': statement['balance_start'],
                    'balance_end_real': statement['balance_end_real'],
                })
                coda_st_ids.append(coda_st_id)

                # check duplicates for CODA's of type 'normal'
                discard = False
                if statement['type'] == 'normal' and statement['discard_dup']:
                    dup_ids = bank_st_obj.search(cr, uid, [('name', '=', statement['name']), ('company_id', '=', company_id)])
                    if dup_ids:
                        discard = True
                        statement['type'] = 'info'  # don't create a bank statement for duplicates
                        statement['coda_parsing_note'] += _("\n\nThe Bank Statement %s already exists, hence no duplicate Bank Statement has been created." \
                        "\nSelect the 'CODA Bank Statement' to check the contents of %s.") \
                        % (statement['name'], statement['name'])

                # create only bank statement for CODA's of type 'normal'
                if statement['type'] == 'normal' and not discard:
                    context.update({'ebanking_import': 1})
                    journal = journal_obj.browse(cr, uid, statement['journal_id'], context=context)
                    balance_start_check_date = statement['first_transaction_date'] or statement['date']
                    cr.execute('SELECT balance_end_real \
                        FROM account_bank_statement \
                        WHERE journal_id = %s and date <= %s \
                        ORDER BY date DESC,id DESC LIMIT 1', (statement['journal_id'], balance_start_check_date))
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
                    if balance_start_check != statement['balance_start']:
                        balance_start_err_string = _('\nThe CODA Statement %s Starting Balance (%.2f) does not correspond with the previous Closing Balance (%.2f) in journal %s!')  \
                            % (statement['name'], statement['balance_start'], balance_start_check, journal.name)
                        if statement['balance_start_enforce']:
                            nb_err += 1
                            err_string += balance_start_err_string
                            break
                        else:
                            statement['coda_parsing_note'] += '\n' + balance_start_err_string

                    st_vals = {
                        'name': statement['name'],
                        'journal_id': statement['journal_id'],
                        'coda_statement_id': coda_st_id,
                        'date': statement['new_balance_date'],
                        'period_id': statement['period_id'],
                        'balance_start': statement['balance_start'],
                        'balance_end_real': statement['balance_end_real'],
                        'state': 'draft',
                    }
                    st_hook_error, st_vals = self._statement_hook(cr, uid, statement['coda_bank_params'], st_vals, context=context)
                    if st_hook_error:
                        nb_err += 1
                        err_string += st_hook_error
                        break
                    bk_st_id = bank_st_obj.create(cr, uid, st_vals, context=context)
                    bk_st_ids.append(bk_st_id)
                    coda_st_obj.write(cr, uid, [coda_st_id], {'statement_id': bk_st_id}, context=context)

                st_line_seq = 0

                for x in lines:
                    line = lines[x]

                    if not line['type'] == 'communication':
                        if line['trans_family'] in st_line_name_families:
                            line['name'] = get_st_line_name(line, context)
                        if line['type'] == 'information':
                            if line['struct_comm_type'] in parse_comms_info:
                                line['name'], line['communication'] = parse_comm_info(self, cr, uid, line, comm_type_table, context)
                            elif line['struct_comm_type'] in parse_comms_move:
                                line['name'], line['communication'] = parse_comm_move(self, cr, uid, line, comm_type_table, context)
                        elif line['struct_comm_type'] in parse_comms_move:
                                line['name'], line['communication'] = parse_comm_move(self, cr, uid, line, comm_type_table, context)

                    # handling non-transactional records : line['type'] in ['information', 'communication']

                    if line['type'] == 'information':

                        #Check if this line can be deleted. glob_id_stack marked as undefined here
                        line['globalisation_id'] = glob_id_stack[-1][2]
                        line_note = _('Transaction Type' ': %s - %s'                \
                            '\nTransaction Family: %s - %s'                         \
                            '\nTransaction Code: %s - %s'                           \
                            '\nTransaction Category: %s - %s'                       \
                            '\nStructured Communication Type: %s - %s'              \
                            '\nCommunication: %s')                                  \
                            % (line['trans_type'], line['trans_type_desc'],
                              line['trans_family'], line['trans_family_desc'],
                              line['trans_code'], line['trans_code_desc'],
                              line['trans_category'], line['trans_category_desc'],
                              line['struct_comm_type'], line['struct_comm_type_desc'],
                              line['communication'])

                        coda_st_line_obj.create(cr, uid, {
                                   'sequence': line['sequence'],
                                   'ref': line['ref'],
                                   'name': line['name'].strip() or '/',
                                   'type': 'information',
                                   'date': line['entry_date'],
                                   'statement_id': coda_st_id,
                                   'note': line_note,
                                   })

                    elif line['type'] == 'communication':

                        line_note = _('Free Communication:\n %s')                  \
                            % (line['communication'])

                        coda_st_line_obj.create(cr, uid, {
                                   'sequence': line['sequence'],
                                   'ref': line['ref'],
                                   'name': line['name'].strip() or '/',
                                   'type': 'communication',
                                   'date': statement['date'],
                                   'statement_id': coda_st_id,
                                   'note': line_note,
                                   })

                    # handling transactional records, # line['type'] in ['globalisation', 'general', 'supplier', 'customer']

                    else:

                        if line['ref_move_detail'] == '0000':
                            glob_id_stack = [(0, '', 0, '')]  # initialise stack with tuples (glob_lvl_flag, glob_code, glob_id, glob_name)

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

                        line_note = _('Partner Name: %s \nPartner Account Number: %s' \
                            '\nTransaction Type: %s - %s'                             \
                            '\nTransaction Family: %s - %s'                           \
                            '\nTransaction Code: %s - %s'                             \
                            '\nTransaction Category: %s - %s'                         \
                            '\nStructured Communication Type: %s - %s'                \
                            '\nPayment Reference: %s'                                 \
                            '\nCommunication: %s')                                    \
                            % (line['counterparty_name'], line['counterparty_number'],
                              line['trans_type'], line['trans_type_desc'],
                              line['trans_family'], line['trans_family_desc'],
                              line['trans_code'], line['trans_code_desc'],
                              line['trans_category'], line['trans_category_desc'],
                              line['struct_comm_type'], line['struct_comm_type_desc'],
                              line['payment_reference'],
                              line['communication'])

                        if line['type'] == 'globalisation':

                            coda_st_line_obj.create(cr, uid, {
                                   'sequence': line['sequence'],
                                   'ref': line['ref'],
                                   'name': line['name'].strip() or '/',
                                   'type': 'globalisation',
                                   'val_date': line['val_date'],
                                   'date': line['entry_date'],
                                   'globalisation_level': line['glob_lvl_flag'],
                                   'globalisation_amount': line['globalisation_amount'],
                                   'globalisation_id': line['globalisation_id'],
                                   'partner_id': line['partner_id'] or 0,
                                   'account_id': line['account_id'],
                                   'payment_reference': line['payment_reference'],
                                   'statement_id': coda_st_id,
                                   'note': line_note,
                                   })

                        else:       # line['type'] in ['general', 'supplier', 'customer']

                            if glob_lvl_flag == 0:
                                line['globalisation_id'] = glob_id_stack[-1][2]
                            if not line['account_id']:
                                    line['account_id'] = awaiting_acc

                            coda_st_line_obj.create(cr, uid, {
                                   'sequence': line['sequence'],
                                   'ref': line['ref'],
                                   'name': line['name'].strip() or '/',
                                   'type': line['type'],
                                   'val_date': line['val_date'],
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
                                   'payment_reference': line['payment_reference'],
                                   'statement_id': coda_st_id,
                                   'note': line_note,
                                   })

                            if statement['type'] == 'normal':
                                if line['amount'] != 0.0:
                                    st_line_seq += 1
                                    voucher_id = False
                                    line_name = line['name'].strip()
                                    if not line_name:
                                        if line['globalisation_id']:
                                            line_name = glob_id_stack[-1][3] or '/'
                                        else:
                                            line_name = '/'

                                    if line['reconcile']:

                                        move_line = move_line_obj.browse(cr, uid, line['reconcile'], context=context)
                                        company_currency_id = journal.company_id.currency_id.id
                                        currency_id = journal.currency.id
                                        if currency_id and currency_id != company_currency_id:
                                            multi_currency = True
                                        else:
                                            multi_currency = False
                                        context_multi_currency = context.copy()
                                        context_multi_currency.update({'date': line['entry_date']})

                                        line_cr_ids = []
                                        line_dr_ids = []
                                        amount_remaining = abs(line['amount'])

                                        #for entry in entries:
                                        if move_line.reconcile_partial_id:
                                            amount_original = abs(move_line.amount_residual_currency)
                                        else:
                                            amount_original = move_line.credit or move_line.debit
                                            if multi_currency:
                                                if move_line.currency_id and move_line.amount_currency:
                                                    amount_original = abs(move_line.amount_currency)
                                                else:
                                                    amount_original = currency_obj.compute(cr, uid, company_currency_id, currency_id, amount_original, context=context_multi_currency)
                                        if amount_remaining > 0:
                                            amount_voucher_line = min(amount_original, abs(amount_remaining))
                                            amount_remaining -= amount_voucher_line
                                        else:
                                            amount_voucher_line = 0.0
                                        voucher_line_vals = {
                                            'name': move_line.name,
                                            'account_id': move_line.account_id.id,
                                            'amount': amount_voucher_line,
                                            'reconcile': amount_voucher_line == amount_original,
                                            'type': move_line.credit and 'dr' or 'cr',
                                            'move_line_id': move_line.id,
                                        }
                                        if voucher_line_vals['type'] == 'cr':
                                            line_cr_ids += [(0, 0, voucher_line_vals)]
                                        else:
                                            line_dr_ids += [(0, 0, voucher_line_vals)]

                                        voucher_vals = {
                                            'type': line['type'] == 'supplier' and 'payment' or 'receipt',
                                            'name': line_name,
                                            'date': line['val_date'],
                                            'journal_id': statement['journal_id'],
                                            'account_id': journal.default_credit_account_id.id,
                                            'line_cr_ids': line_cr_ids,
                                            'line_dr_ids': line_dr_ids,
                                            'pre_line': len(line_dr_ids) > 0 and True or False,
                                            'period_id': statement['period_id'],
                                            'currency_id': journal.currency and journal.currency.id or journal.company_id.currency_id.id,
                                            'company_id': journal.company_id.id,
                                            'state': 'draft',
                                            'amount': abs(line['amount']),
                                            'reference': line['ref'],
                                            'number': statement['name'] + '/' + str(st_line_seq),
                                            'partner_id': line['partner_id'],
                                        }

                                        #_logger.warn('voucher_vals=%s, context=%s', voucher_vals, context)
                                        context['journal_id'] = journal.id  # add journal to context for __get_payment_rate_currency method
                                        if line_cr_ids or line_dr_ids:
                                            voucher_id = voucher_obj.create(cr, uid, voucher_vals, context=context)
                                        else:
                                            raise osv.except_osv(_('Error!'), _("Reconcile error while processing line with ref '%s' ! " \
                                                  "\nPlease report this issue via your OpenERP support channel.") % line['ref'])

                                    # override default account mapping by mappings defined in rules engine
                                    if statement['account_mapping_ids']:
                                        kwargs = {
                                            'coda_bank_account_id': statement['coda_bank_account_id'],
                                            'trans_type_id': line['trans_type_id'],
                                            'trans_family_id': line['trans_family_id'],
                                            'trans_code_id': line['trans_code_id'],
                                            'trans_category_id': line['trans_category_id'],
                                            'struct_comm_type_id': line['struct_comm_type_id'],
                                            'partner_id': line['partner_id'],
                                            'context': context,
                                        }
                                        account_id = account_mapping_obj.account_id_get(cr, uid, **kwargs)
                                        if account_id:
                                            line['account_id'] = account_id
                                    st_line_vals = {
                                           'ref': line['ref'],
                                           'name': line_name,
                                           'type': line['type'],
                                           'val_date': line['val_date'],
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
                                            }

                                    st_lines_vals = self._st_line_hook(cr, uid, statement['coda_bank_params'], st_line_vals, context=context)
                                    if not st_lines_vals:
                                        # removal of lines by the _coda_parsing_hook currently not supported :
                                        # this qould require resequencing/renaming of linked vouchers & moves as well as removal of associated voucher/moves
                                        err_string += _('\nError in _st_line_hook while processing CODA Statement %s for Bank Account %s!')  \
                                            % (statement['coda_seq_number'], (statement['acc_number'] + ' (' + statement['currency'] + ') - ' + statement['description']))
                                        nb_err += 1
                                    for st_line_vals in st_lines_vals:
                                        # To DO : update sequence of statement lines and naming of associated vouchers/moves when the hook returns multiple lines
                                        st_line_vals.update({'sequence': st_line_seq})
                                        bank_st_line_obj.create(cr, uid, st_line_vals, context=context)
                                        if st_line_vals['voucher_id']:
                                            voucher = voucher_obj.browse(cr, uid, st_line_vals['voucher_id'], context=context)
                                            move_line = move_line_obj.browse(cr, uid, line['reconcile'], context=context)
                                            if line['amount'] == (line['amount'] > 0 and move_line.debit or -move_line.credit):
                                                wf_service.trg_validate(uid, 'account.voucher', st_line_vals['voucher_id'], 'proforma_voucher', cr)
                                            if voucher.move_id:
                                                move_line_obj.write(cr, uid, [x.id for x in voucher.move_ids], {'statement_id': bk_st_id}, context=context)

                # end 'for x in lines'

                coda_st_obj.write(cr, uid, [coda_st_id], {}, context=context)           # calculate balance
                st_balance = coda_st_obj.read(cr, uid, coda_st_id, ['balance_end', 'balance_end_real'], context=context)
                if st_balance['balance_end'] != st_balance['balance_end_real']:
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
                    % (journal_name,
                      coda_version,
                      statement['coda_seq_number'],
                      statement['paper_nb_seq_number'],
                      (statement['acc_number'] + ' (' + statement['currency'] + ') - ' + statement['description']),
                      statement['acc_holder'],
                      statement['date'], float(statement['balance_start']), float(statement['balance_end_real']),
                      statement['coda_parsing_note'] % {'name': coda_statement['name']})
                if statement.get('separate_application') != '00000':
                    coda_note += _('\nCode Separate Application: %s') % statement['separate_application']                                                  \

            except osv.except_osv, e:
                cr.rollback()
                nb_err += 1
                err_string += _('\nError ! ') + str(e)
                tb = ''.join(format_exception(*exc_info()))
                _logger.error('Application Error while processing Statement %s\n%s',
                    statement.get('name', '/'), tb)
            except Exception, e:
                cr.rollback()
                nb_err += 1
                err_string += _('\nSystem Error : ') + str(e)
                tb = ''.join(format_exception(*exc_info()))
                _logger.error('System Error while processing Statement %s\n%s',
                    statement.get('name', '/'), tb)
            except:
                cr.rollback()
                nb_err += 1
                err_string = _('\nUnknown Error : ') + str(e)
                tb = ''.join(format_exception(*exc_info()))
                _logger.error('Unknown Error while processing Statement %s\n%s',
                    statement.get('name', '/'), tb)

        # end 'for statement in coda_statements'

        coda_note_header = _('CODA File is Imported  :')
        coda_note_footer = _('\n\nNumber of statements : ') + str(len(coda_st_ids))
        err_log = err_log + _('\nNumber of errors : ') + str(nb_err) + '\n'

        if not nb_err:
            note = coda_note_header + coda_note + coda_note_footer
            coda_obj.write(cr, uid, [coda_id], {'note': note})
            cr.commit()
            if batch:
                return None
        else:
            cr.rollback()
            if batch:
                err_code = 'G0002'
                return (err_code, err_string)
            raise osv.except_osv(_('CODA Import failed !'), err_string)

        context.update({'bk_st_ids': bk_st_ids})
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

    def _statement_hook(self, cr, uid, coda_bank_params, st_vals, context=None):
        """
        Use this method to take customer specific actions based upon the bank statement data.
        Returns:
            st_hook_error : False or string with error message
            st_vals
        """
        return False, st_vals

    def _st_line_hook(self, cr, uid, coda_bank_params, st_line_vals, context=None):
        """
        Use this method to adapt the statement line created by the
        CODA parsing to customer specific needs.
        """
        return [st_line_vals]

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
        domain += [('id', 'in', context.get('bk_st_ids', False))]
        action.update({'domain': domain})
        return action

account_coda_import()


def repl_special(s):
    s = s.replace("\'", "\'" + "'")
    return s


def str2date(date_str):
    try:
        return time.strftime('%Y-%m-%d', time.strptime(date_str, '%d%m%y'))
    except:
        return False


def str2time(time_str):
    return time_str[:2] + ':' + time_str[2:]


def str2float(str):
    try:
        return float(str)
    except:
        return 0.0


def list2float(lst):
            try:
                return str2float((lambda s: s[:-3] + '.' + s[-3:])(lst))
            except:
                return 0.0


def number2float(s, d):
    try:
        return float(s[:len(s) - d] + '.' + s[len(s) - d:])
    except:
        return False


def _get_acc_numbers(acc_number):
    #TODO this method is needed because the iban and bank account fields have been merged together. But sometimes we
    #   need to retrieve the normal bank account from the IBAN. This should be globalized and defined as a method on the
    #   bank account class. Each country part of the IBAN area should define its own code to do so.
    acc_number = acc_number.replace(' ', '')
    if acc_number.lower().startswith('be'):
        return [acc_number[4:], acc_number]
    return [acc_number]

from base_iban.base_iban import _ref_iban, _format_iban


def calc_iban_checksum(country, bban):
    bban = bban.replace(' ', '').upper() + country.upper() + '00'
    base = ''
    for c in bban:
        if c.isdigit():
            base += c
        else:
            base += str(ord(c) - ord('A') + 10)
    kk = 98 - int(base) % 97
    return str(kk).rjust(2, '0')


def check_bban(country, bban):
    if country == 'BE':
        try:
            int(bban)
        except:
            return False
        if len(bban) != 12:
            return False
    return True


def check_iban(iban):
    """
    Check the IBAN number (logic partially based upon base_iban module, cf. is_iban_valid method)
    """
    iban = _format_iban(iban).lower()
    if iban[:2] not in _ref_iban:
        return False
    if len(iban) != len(_format_iban(_ref_iban[iban[:2]])):
        return False
    #the four first digits have to be shifted to the end
    iban = iban[4:] + iban[:4]
    #letters have to be transformed into numbers (a = 10, b = 11, ...)
    iban2 = ""
    for char in iban:
        if char.isalpha():
            iban2 += str(ord(char) - 87)
        else:
            iban2 += char
    #iban is correct if modulo 97 == 1
    return int(iban2) % 97 == 1


def get_bank(self, cr, uid, bic, iban):

    country_obj = self.pool.get('res.country')
    bank_obj = self.pool.get('res.bank')

    bank_id = False
    bank_name = False
    feedback = False
    bank_country = iban[:2]
    try:
        bank_country_id = country_obj.search(cr, uid, [('code', '=', bank_country)])[0]
    except:
        feedback = _("\n        Bank lookup failed due to missing Country definition for Country Code '%s' !") \
            % (bank_country)
    else:
        if iban[:2] == 'BE' and 'code' in bank_obj.fields_get_keys(cr, uid):
            # To DO : extend for other countries
            bank_code = iban[4:7]
            if bic:
                bank_ids = bank_obj.search(cr, uid, [('bic', '=', bic), ('code', '=', bank_code), ('country', '=', bank_country_id)])
                if bank_ids:
                    bank_id = bank_ids[0]
                else:
                    bank_id = bank_obj.create(cr, uid, {
                        'name': bic,
                        'code': bank_code,
                        'bic': bic,
                        'country': bank_country_id,
                        })
            else:
                bank_ids = bank_obj.search(cr, uid, [('code', '=', bank_code), ('country', '=', bank_country_id)])
                if bank_ids:
                    bank_id = bank_ids[0]
                    bank_data = bank_obj.read(cr, uid, bank_id, fields=['bic', 'name'])
                    bic = bank_data['bic']
                    bank_name = bank_data['name']
                else:
                    country = country_obj.browse(cr, uid, bank_country_id)
                    feedback = _("\n        Bank lookup failed. Please define a Bank with Code '%s' and Country '%s' !") \
                        % (bank_code, country.name)
        else:
            if not bic:
                feedback = _("\n        Bank lookup failed due to missing BIC in Bank Statement for IBAN '%s' !") \
                    % (iban)
            else:
                bank_ids = bank_obj.search(cr, uid, [('bic', '=', bic), ('country', '=', bank_country_id)])
                if not bank_ids:
                    bank_name = bic
                    bank_id = bank_obj.create(cr, uid, {
                        'name': bank_name,
                        'bic': bic,
                        'country': bank_country_id,
                        })
                else:
                    bank_id = bank_ids[0]

    return bank_id, bic, bank_name, feedback


def update_partner_bank(self, cr, uid, bic, iban, partner_id, counterparty_name):
    partner_bank_obj = self.pool.get('res.partner.bank')
    bank_id = False
    feedback = False
    if check_iban(iban):
        bank_id, bic, bank_name, feedback = get_bank(self, cr, uid, bic, iban)
        if not bank_id:
            return feedback
    else:
        #convert belgian BBAN numbers to IBAN
        if check_bban('BE', iban):
            kk = calc_iban_checksum('BE', iban)
            iban = 'BE' + kk + iban
            bank_id, bic, bank_name, feedback = get_bank(self, cr, uid, bic, iban)
            if not bank_id:
                return feedback

    if bank_id:
        partner_bank_obj.create(cr, uid, {
            'partner_id': partner_id,
            'name': counterparty_name,
            'bank': bank_id,
            'state': 'iban',
            'bank_bic': bic,
            'bank_name': bank_name,
            'acc_number': iban,
            })
    return feedback

indent = '\n' + 8 * ' '
st_line_name_families = ['13', '35', '41', '80']
parse_comms_move = ['100', '101', '102', '103', '105', '106', '107', '108', '111', '113', '114', '115', '121', '122', '123', '124', '125', '126', '127']
parse_comms_info = ['001', '002', '004', '005', '006', '007', '107', '008', '009', '010', '011']


def get_st_line_name(line, context):
    #_logger.warn('get_st_line_name - entry').warn('ref = %s, family = %s, code = %s, categ = %s', line['ref'], line['trans_family'], line['trans_code'], line['trans_category'])
    st_line_name = line['name']

    if line['trans_family'] == '35' and line['trans_code'] in ['01', '37']:
        st_line_name = ', '.join([_('Closing'), line['trans_code_desc'], line['trans_category_desc']])

    if line['trans_family'] in ['13', '41']:
        st_line_name = ', '.join([line['trans_family_desc'], line['trans_code_desc'], line['trans_category_desc']])

    if line['trans_family'] in ['80']:
        st_line_name = ', '.join([line['trans_code_desc'], line['trans_category_desc']])

    return st_line_name


def parse_comm_move(self, cr, uid, line, comm_type_table, context):
    #_logger.warn('parse_comm_move - entry, ref = %s, family = %s, code = %s, categ = %s, comm_type = %s, name = %s', line['ref'], line['trans_family'], line['trans_code'], line['trans_category'], line['struct_comm_type'], line['name'])
    comm_type = line['struct_comm_type']
    comm = st_line_comm = line['communication']
    st_line_name = line['name']

    if comm_type in ['115', '121', '122', '126']:
        _logger.warn('The parsing of Structured Commmunication Type %s has not yet been implemented. ' \
            'Please contact Noviat (info@noviat.be) for more information about the development roadmap', comm_type)

    if comm_type == '100':
        st_line_name = _('Payment with ISO 11649 structured format communication')
        st_line_comm = '\n' + indent + _('Payment with a structured format communication applying the ISO standard 11649') + ':'
        st_line_comm += indent + _('Structured creditor reference to remittance information')
        st_line_comm += indent + comm

    if comm_type in ['101', '102']:
        st_line_name = st_line_comm = '+++' + comm[0:3] + '/' + comm[3:7] + '/' + comm[7:12] + '+++'

    if comm_type == '103':
        st_line_name = ', '.join([line['trans_family_desc'], _('Number')])
        st_line_comm = comm

    if comm_type == '105':
        st_line_name = filter(lambda x: comm_type == x['code'], comm_type_table)[0]['description']
        amount_1 = list2float(comm[0:15])
        amount_2 = list2float(comm[15:30])
        rate = number2float(comm[30:42], 8)
        currency = comm[42:45]
        struct_format_comm = comm[45:57].strip()
        country_code = comm[57:59]
        amount_3 = list2float(comm[59:74])
        st_line_comm = '\n' + indent + st_line_name + indent + _('Gross amount in the currency of the account') + ': %.2f' % amount_1
        st_line_comm += indent + _('Gross amount in the original currency') + ': %.2f' % amount_2
        st_line_comm += indent + _('Rate') + ': %.4f' % rate
        st_line_comm += indent + _('Currency') + ': %s' % currency
        st_line_comm += indent + _('Structured format communication') + ': %s' % struct_format_comm
        st_line_comm += indent + _('Country code of the principal') + ': %s' % country_code
        st_line_comm += indent + _('Equivalent in EUR') + ': %.2f' % amount_3

    if comm_type == '106':
        if not st_line_name and line['trans_family'] not in st_line_name_families:
            st_line_name = _('VAT, withholding tax on income, commission, etc.')
        interest = comm[30:42].strip('0')
        st_line_comm = '\n' + indent + st_line_name + indent + _('Equivalent in the currency of the account') + ': %.2f' % list2float(comm[0:15])
        st_line_comm += indent + _('Amount on which % is calculated') + ': %.2f' % list2float(comm[15:30])
        st_line_comm += indent + _('Percent') + ': %.4f' % number2float(comm[30:42], 8)
        st_line_comm += indent + (comm[42] == 1 and _('Minimum applicable') or _('Minimum not applicable'))
        st_line_comm += indent + _('Equivalent in EUR') + ': %.2f' % list2float(comm[43:58])

    if comm_type == '107':
        paid_refusals = {
            '0': _('paid'),
            '1': _('direct debit cancelled or nonexistent'),
            '2': _('refusal - other reason'),
            'D': _('payer disagrees'),
            'E': _('direct debit number linked to another identification number of the creditor')}
        st_line_name = _('Direct debit - DOM\'80')
        direct_debit_number = comm[0:12].strip()
        pivot_date = str2date(comm[12:18])
        comm_zone = comm[18:48]
        paid_refusal = paid_refusals.get(comm[48], '')
        creditor_number = comm[49:60].strip()
        st_line_comm = '\n' + indent + st_line_name + indent + _('Direct Debit Number') + ': %s' % direct_debit_number
        st_line_comm += indent + _('Central (Pivot) Date') + ': %s' % pivot_date
        st_line_comm += indent + _('Communication Zone') + ': %s' % comm_zone
        st_line_comm += indent + _('Paid or reason for refusal') + ': %s' % paid_refusal
        st_line_comm += indent + _("Creditor's Number") + ': %s' % creditor_number

    if comm_type == '108':
        st_line_name = _('Closing, period from %s to %s') % (str2date(comm[42:48]), str2date(comm[48:54]))
        interest = comm[30:42].strip('0')
        st_line_comm = '\n' + indent + st_line_name + indent + _('Equivalent in the currency of the account') + ': %.2f' % list2float(comm[0:15])
        if interest:
            st_line_comm += indent + _('Interest rates, calculation basis') + ': %.2f' % list2float(comm[15:30]) + \
                indent + _('Interest') + ': %.2f' % list2float(comm[30:42])

    if comm_type == '111':
        card_schemes = {
            '1': 'Bancontact/Mister Cash',
            '2': _('Private'),
            '3': 'Maestro',
            '5': 'TINA',
            '9': _('Other')}
        trans_types = {
            '1': _('Withdrawal'),
            '2': _('Cumulative on network'),
            '7': _('Distribution sector'),
            '8': _('Teledata'),
            '9': _('Fuel')}
        st_line_name = _('POS credit - globalisation')
        card_scheme = card_schemes.get(comm[0], '')
        pos_number = comm[1:7].strip()
        period_number = comm[7:10].strip()
        first_sequence_number = comm[10:16].strip()
        trans_first_date = str2date(comm[16:22])
        last_sequence_number = comm[22:28].strip()
        trans_last_date = str2date(comm[28:34])
        trans_type = trans_types.get(comm[34], '')
        terminal_name = comm[35:50].strip()
        terminal_city = comm[51:60].strip()
        st_line_comm = '\n' + indent + st_line_name + indent + _('Card Scheme') + ': %s' % card_scheme
        st_line_comm += indent + _('POS Number') + ': %s' % pos_number
        st_line_comm += indent + _('Period Number') + ': %s' % period_number
        st_line_comm += indent + _('First Transaction Sequence Number') + ': %s' % first_sequence_number
        st_line_comm += indent + _('Date of first transaction') + ': %s' % trans_first_date
        st_line_comm += indent + _('Last Transaction Sequence Number') + ': %s' % last_sequence_number
        st_line_comm += indent + _('Date of last transaction') + ': %s' % trans_last_date
        st_line_comm += indent + _('Transaction Type') + ': %s' % trans_type
        st_line_comm += indent + _('Terminal Identification') + ': %s' % terminal_name + ', ' + terminal_city

    if comm_type == '113':
        card_schemes = {
            '1': 'Bancontact/Mister Cash',
            '2': 'Maestro',
            '3': _('Private'),
            '9': _('Other')}
        trans_types = {
            '1': _('Withdrawal'),
            '2': _('Proton loading'),
            '3': _('Reimbursement Proton balance'),
            '4': _('Reversal of purchases'),
            '7': _('Distribution sector'),
            '8': _('Teledata'),
            '9': _('Fuel')}
        product_codes = {
            '01': _('premium with lead substitute'),
            '02': _('europremium'),
            '03': _('diesel'),
            '04': _('LPG'),
            '06': _('premium plus 98 oct'),
            '07': _('regular unleaded'),
            '08': _('domestic fuel oil'),
            '09': _('lubricants'),
            '10': _('petrol'),
            '11': _('premium 99+'),
            '12': _('Avgas'),
            '16': _('other types'),
            }
        st_line_name = _('ATM/POS debit')
        card_number = comm[0:16].strip()
        card_scheme = card_schemes.get(comm[16], '')
        terminal_number = comm[17:23].strip()
        sequence_number = comm[23:29].strip()
        trans_date = comm[29:35].strip() and str2date(comm[29:35]) or ''
        trans_hour = comm[35:39].strip() and str2time(comm[35:39]) or ''
        trans_type = trans_types.get(comm[39], '')
        terminal_name = comm[40:56].strip()
        terminal_city = comm[56:66].strip()
        orig_amount = comm[66:81].strip() and list2float(comm[66:81])
        rate = number2float(comm[81:93], 8)
        currency = comm[93:96]
        volume = number2float(comm[96:101], 2)
        product_code = product_codes.get(comm[101:103], '')
        unit_price = number2float(comm[103:108], 2)
        st_line_comm = '\n' + indent + st_line_name + indent + _('Card Number') + ': %s' % card_number
        st_line_comm += indent + _('Card Scheme') + ': %s' % card_scheme
        if terminal_number:
            st_line_comm += indent + _('Terminal Number') + ': %s' % terminal_number
        st_line_comm += indent + _('Transaction Sequence Number') + ': %s' % sequence_number
        st_line_comm += indent + _('Time') + ': %s' % trans_date + ' ' + trans_hour
        st_line_comm += indent + _('Transaction Type') + ': %s' % trans_type
        st_line_comm += indent + _('Terminal Identification') + ': %s' % terminal_name + ', ' + terminal_city
        if orig_amount:
            st_line_comm += indent + _('Original Amount') + ': %.2f' % orig_amount
            st_line_comm += indent + _('Rate') + ': %.4f' % rate
            st_line_comm += indent + _('Currency') + ': %s' % currency
        if volume:
            st_line_comm += indent + _('Volume') + ': %.2f' % volume
        if product_code:
            st_line_comm += indent + _('Product Code') + ': %s' % product_code
        if unit_price:
            st_line_comm += indent + _('Unit Price') + ': %.2f' % unit_price

    if comm_type == '114':
        card_schemes = {
            '1': 'Bancontact/Mister Cash',
            '2': 'Maestro',
            '3': _('Private'),
            '5': 'TINA',
            '9': _('Other')}
        trans_types = {
            '1': _('Withdrawal'),
            '7': _('Distribution sector'),
            '8': _('Teledata'),
            '9': _('Fuel')}
        st_line_name = _('POS credit - individual transaction')
        card_scheme = card_schemes.get(comm[0], '')
        pos_number = comm[1:7].strip()
        period_number = comm[7:10].strip()
        sequence_number = comm[10:16].strip()
        trans_date = str2date(comm[16:22])
        trans_hour = str2time(comm[22:26])
        trans_type = trans_types.get(comm[26], '')
        terminal_name = comm[27:43].strip()
        terminal_city = comm[43:53].strip()
        trans_reference = comm[53:69].strip()
        st_line_comm = '\n' + indent + st_line_name + indent + _('Card Scheme') + ': %s' % card_scheme
        st_line_comm += indent + _('POS Number') + ': %s' % pos_number
        st_line_comm += indent + _('Period Number') + ': %s' % period_number
        st_line_comm += indent + _('Transaction Sequence Number') + ': %s' % sequence_number
        st_line_comm += indent + _('Time') + ': %s' % trans_date + ' ' + trans_hour
        st_line_comm += indent + _('Transaction Type') + ': %s' % trans_type
        st_line_comm += indent + _('Terminal Identification') + ': %s' % terminal_name + ', ' + terminal_city
        st_line_comm += indent + _('Transaction Reference') + ': %s' % trans_reference

    if comm_type == '123':
        starting_date = str2date(comm[0:6])
        maturity_date = comm[6:12] == '999999' and _('guarantee without fixed term') or str2date(comm[0:6])
        basic_amount = list2float(comm[12:27])
        percent = number2float(comm[27:39], 8)
        term = comm[39:43].lstrip('0')
        minimum = comm[43] == '1' and True or False
        guarantee_number = comm[44:57].strip()
        st_line_comm = '\n' + indent + st_line_name + indent + _('Starting Date') + ': %s' % starting_date
        st_line_comm += indent + _('Maturity Date') + ': %s' % maturity_date
        st_line_comm += indent + _('Basic Amount') + ': %.2f' % basic_amount
        st_line_comm += indent + _('Percentage') + ': %.4f' % percent
        st_line_comm += indent + _('Term in days') + ': %s' % term
        st_line_comm += indent + (minimum and _('Minimum applicable') or _('Minimum not applicable'))
        st_line_comm += indent + _('Guarantee Number') + ': %s' % guarantee_number

    if comm_type == '124':
        card_issuers = {
            '1': 'Mastercard',
            '2': 'Visa',
            '3': 'American Express',
            '4': 'Diners Club',
            '9': _('Other')}
        st_line_name = _('Settlement credit cards')
        card_number = comm[0:20].strip()
        card_issuer = card_issuers.get(comm[20], '')
        invoice_number = comm[21:33].strip()
        identification_number = comm[33:48].strip()
        date = comm[48:54].strip() and str2date(comm[48:54]) or ''
        st_line_comm = '\n' + indent + st_line_name + indent + _('Card Number') + ': %s' % card_number
        st_line_comm += indent + _('Issuing Institution') + ': %s' % card_issuer
        st_line_comm += indent + _('Invoice Number') + ': %s' % invoice_number
        st_line_comm += indent + _('Identification Number') + ': %s' % identification_number
        st_line_comm += indent + _('Date') + ': %s' % date

    if comm_type == '125':
        if line['trans_family'] not in st_line_name_families:
            st_line_name = _('Credit')
        credit_account = comm[0:27].strip()
        if check_bban('BE', credit_account):
            credit_account = '-'.join([credit_account[:3], credit_account[3:10], credit_account[10:]])
        old_balance = list2float(comm[27:42])
        new_balance = list2float(comm[42:57])
        amount = list2float(comm[57:72])
        currency = comm[72:75]
        start_date = str2date(comm[75:81])
        end_date = str2date(comm[81:87])
        rate = number2float(comm[87:99], 8)
        trans_reference = comm[99:112].strip()
        st_line_comm = '\n' + indent + st_line_name + indent + _('Credit Account Number') + ': %s' % credit_account
        st_line_comm += indent + _('Old Balance') + ': %.2f' % old_balance
        st_line_comm += indent + _('New Balance') + ': %.2f' % new_balance
        st_line_comm += indent + _('Amount') + ': %.2f' % amount
        st_line_comm += indent + _('Currency') + ': %s' % currency
        st_line_comm += indent + _('Starting Date') + ': %s' % start_date
        st_line_comm += indent + _('End Date') + ': %s' % end_date
        st_line_comm += indent + _('Nominal Interest Rate or Rate of Charge') + ': %.4f' % rate
        st_line_comm += indent + _('Transaction Reference') + ': %s' % trans_reference

    if comm_type == '127':
        direct_debit_types = {
            '0': _('unspecified'),
            '1': _('recurrent'),
            '2': _('one-off'),
            '3': _('1-st (recurrent)'),
            '4': _('last (recurrent)')}
        direct_debit_schemes = {
            '0': _('unspecified'),
            '1': _('SEPA core'),
            '2': _('SEPA B2B')}
        paid_refusals = {
            '0': _('paid'),
            '1': _('technical problem'),
            '2': _('refusal - reason not specified'),
            '3': _('debtor disagrees'),
            '4': _('debtor\'s account problem')}
        R_types = {
            '0': _('paid'),
            '1': _('reject'),
            '2': _('return'),
            '3': _('refund'),
            '4': _('reversal'),
            '5': _('cancellation')}
        st_line_name = _('European direct debit (SEPA)')
        settlement_date = str2date(comm[0:6])
        direct_debit_type = direct_debit_types.get(comm[6], '')
        direct_debit_scheme = direct_debit_schemes.get(comm[7], '')
        paid_refusal = paid_refusals.get(comm[8], '')
        creditor_id = comm[9:44].strip()
        mandate_ref = comm[44:79].strip()
        comm_zone = comm[79:141]
        R_type = R_types.get(comm[141], '')
        reason = comm[142:146].strip()
        st_line_comm = '\n' + indent + st_line_name + indent + _('Settlement_Date') + ': %s' % settlement_date
        st_line_comm += indent + _('Direct Debit Type') + ': %s' % direct_debit_type
        st_line_comm += indent + _('Direct Debit Scheme') + ': %s' % direct_debit_scheme
        st_line_comm += indent + _('Paid or reason for refusal') + ': %s' % paid_refusal
        st_line_comm += indent + _('Creditor\'s Identification Code') + ': %s' % creditor_id
        st_line_comm += indent + _('Mandate Reference') + ': %s' % mandate_ref
        st_line_comm += indent + _('Communication') + ': %s' % comm_zone
        st_line_comm += indent + _('R transaction Type') + ': %s' % R_type
        st_line_comm += indent + _('Reason') + ': %s' % reason

    return st_line_name, st_line_comm


def parse_comm_info(self, cr, uid, line, comm_type_table, context):
    comm_type = line['struct_comm_type']
    comm = st_line_comm = line['communication']
    st_line_name = line['name']

    if comm_type == '001':
        st_line_name = filter(lambda x: comm_type == x['code'], comm_type_table)[0]['description']
        st_line_comm = '\n' + indent + st_line_name + indent + _('Name') + ': %s' % comm[0:70].strip()
        st_line_comm += indent + _('Street') + ': %s' % comm[70:105].strip()
        st_line_comm += indent + _('Locality') + ': %s' % comm[105:140].strip()
        st_line_comm += indent + _('Identification Code') + ': %s' % comm[140:175].strip()

    if comm_type in ['002', '004', '005']:
        st_line_name = filter(lambda x: comm_type == x['code'], comm_type_table)[0]['description']
        st_line_comm = comm.strip()

    if comm_type == '006':
        amount = (comm[48] == '1' and '-' or '') + ('%.2f' % list2float(comm[33:48])) + ' ' + comm[30:33]
        st_line_name = filter(lambda x: comm_type == x['code'], comm_type_table)[0]['description']
        st_line_comm = '\n' + indent + st_line_name + indent + _('Description of the detail') + ': %s' % comm[0:30].strip()
        st_line_comm += indent + _('Amount') + ': %s' % amount
        st_line_comm += indent + _('Category') + ': %s' % comm[49:52].strip()

    if comm_type not in ['001', '002', '004', '005', '006']:
        _logger.warn('The parsing of Structured Commmunication Type %s has not yet been implemented. ' \
            'Please contact Noviat (info@noviat.be) for more information about the development roadmap', comm_type)

    return st_line_name, st_line_comm
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
