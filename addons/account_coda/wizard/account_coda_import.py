# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

def str2date(date_str):
    return time.strftime("%y/%m/%d", time.strptime(date_str, "%d%m%y"))

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

class account_coda_import(osv.osv_memory):
    _name = 'account.coda.import'
    _description = 'Account Coda Import'
    _columns = {
            'journal_id': fields.many2one('account.journal', 'Bank Journal', required=True),
            'def_payable': fields.many2one('account.account', 'Default Payable Account', domain=[('type', '=', 'payable')], required=True, help= 'Set here the payable account that will be used, by default, if the partner is not found'),
            'def_receivable': fields.many2one('account.account', 'Default Receivable Account', domain=[('type', '=', 'receivable')], required=True, help= 'Set here the receivable account that will be used, by default, if the partner is not found',),
            'awaiting_account': fields.many2one('account.account', 'Default Account for Unrecognized Movement', domain=[('type', '=', 'liquidity')], required=True, help= 'Set here the default account that will be used, if the partner is found but does not have the bank account, or if he is domiciled'),
            'coda': fields.binary('Coda File', required=True),
            'note':fields.text('Log'),
    }

    def coda_parsing(self, cr, uid, ids, context=None):

        journal_obj=self.pool.get('account.journal')
        account_period_obj = self.pool.get('account.period')
        partner_bank_obj = self.pool.get('res.partner.bank')
        bank_statement_obj = self.pool.get('account.bank.statement')
        bank_statement_line_obj = self.pool.get('account.bank.statement.line')
        voucher_obj = self.pool.get('account.voucher')
        voucher_line_obj = self.pool.get('account.voucher.line')
        account_coda_obj = self.pool.get('account.coda')
        mod_obj = self.pool.get('ir.model.data')
        line_obj = self.pool.get('account.move.line')

        if context is None:
            context = {}

        data = self.browse(cr, uid, ids, context=context)[0]

        codafile = data.coda
        journal_code = data.journal_id.code

        period = account_period_obj.find(cr, uid, context=context)[0]
        def_pay_acc = data.def_payable.id
        def_rec_acc = data.def_receivable.id

        err_log = "Errors:\n------\n"
        nb_err=0
        std_log=''
        str_log1 = "Coda File is Imported:  "
        str_not=''
        str_not1=''

        bank_statements = []
        bank_statement = {}
        recordlist = base64.decodestring(codafile).split('\n')
        recordlist.pop()
        for line in recordlist:
            if line[0] == '0':
                # header data

                bank_statement["bank_statement_line"]={}
                bank_statement_lines = {}
                bank_statement['date'] = str2date(line[5:11])
                bank_statement['journal_id']=data.journal_id.id
                period_id = account_period_obj.search(cr, uid, [('date_start', '<=', time.strftime('%Y-%m-%d', time.strptime(bank_statement['date'], "%y/%m/%d"))), ('date_stop', '>=', time.strftime('%Y-%m-%d', time.strptime(bank_statement['date'], "%y/%m/%d")))])
                bank_statement['period_id'] = period_id and period_id[0] or False
                bank_statement['state']='draft'
            elif line[0] == '1':
                # old balance data
                bal_start = list2float(line[43:58])
                if line[42] == '1':
                    bal_start = - bal_start
                bank_statement["balance_start"]= bal_start
                bank_statement["acc_number"]=line[5:17]
                bank_statement["acc_holder"]=line[64:90]
                bank_statement['name'] = journal_code + ' ' + str(line[2:5])

            elif line[0]=='2':
                # movement data record 2
                if line[1]=='1':
                    # movement data record 2.1
                    if bank_statement_lines.has_key(line[2:6]):
                        continue
                    st_line = {}
                    st_line['extra_note'] = ''
                    st_line['statement_id']=0
                    st_line['ref'] = line[2:10]
                    st_line['date'] = time.strftime('%Y-%m-%d', time.strptime(str2date(line[115:121]), "%y/%m/%d")),
                    st_line_amt = list2float(line[32:47])

                    if line[61]=='1':
                        st_line['toreconcile'] = True
                        st_line['name']=line[65:77]
                    else:
                        st_line['toreconcile'] = False
                        st_line['name']=line[62:115]

                    st_line['free_comm'] = st_line['name']
                    st_line['val_date']=time.strftime('%Y-%m-%d', time.strptime(str2date(line[47:53]), "%y/%m/%d")),
                    st_line['entry_date']=time.strftime('%Y-%m-%d', time.strptime(str2date(line[115:121]), "%y/%m/%d")),
                    st_line['partner_id']=0
                    if line[31] == '1':
                        st_line_amt = - st_line_amt
                        st_line['account_id'] = def_pay_acc
                    else:
                        st_line['account_id'] = def_rec_acc
                    st_line['amount'] = st_line_amt
                    bank_statement_lines[line[2:6]]=st_line
                    bank_statement["bank_statement_line"]=bank_statement_lines
                elif line[1] == '2':
                    st_line_name = line[2:6]
                    bank_statement_lines[st_line_name].update({'account_id': data.awaiting_account.id})

                elif line[1] == '3':
                    # movement data record 3.1
                    st_line_name = line[2:6]
                    st_line_partner_acc = str(line[10:47]).strip()
                    cntry_number=line[10:47].strip()
                    contry_name=line[47:125].strip()
                    bank_ids = partner_bank_obj.search(cr, uid, [('acc_number', '=', st_line_partner_acc)])
                    bank_statement_lines[st_line_name].update({'cntry_number': cntry_number, 'contry_name': contry_name})
                    if bank_ids:
                        bank = partner_bank_obj.browse(cr, uid, bank_ids[0], context=context)
                        if line and bank.partner_id:
                            bank_statement_lines[st_line_name].update({'partner_id': bank.partner_id.id})
                            if bank_statement_lines[st_line_name]['amount'] < 0:
                                bank_statement_lines[st_line_name].update({'account_id': bank.partner_id.property_account_payable.id})
                            else:
                                bank_statement_lines[st_line_name].update({'account_id': bank.partner_id.property_account_receivable.id})
                    else:
                        nb_err += 1
                        err_log += _('The bank account %s is not defined for the partner %s.\n')%(cntry_number, contry_name)
                        bank_statement_lines[st_line_name].update({'account_id': data.awaiting_account.id})

                    bank_statement["bank_statement_line"]=bank_statement_lines
            elif line[0]=='3':
                if line[1] == '1':
                    st_line_name = line[2:6]
                    bank_statement_lines[st_line_name]['extra_note'] += '\n' + line[40:113]
                elif line[1] == '2':
                    st_line_name = line[2:6]
                    bank_statement_lines[st_line_name]['extra_note'] += '\n' + line[10:115]
                elif line[1] == '3':
                    st_line_name = line[2:6]
                    bank_statement_lines[st_line_name]['extra_note'] += '\n' + line[10:100]
            elif line[0]=='8':
                # new balance record
                bal_end = list2float(line[42:57])
                if line[41] == '1':
                    bal_end = - bal_end
                bank_statement["balance_end_real"]= bal_end

            elif line[0]=='9':
                # footer record

                bank_statements.append(bank_statement)
        #end for
        bkst_list=[]
        for statement in bank_statements:
            try:
                bk_st_id =bank_statement_obj.create(cr, uid, {
                    'journal_id': statement.get('journal_id',False),
                    'date': time.strftime('%Y-%m-%d', time.strptime(statement.get('date',time.strftime('%Y-%m-%d')), "%y/%m/%d")),
                    'period_id': statement.get('period_id',False) or period,
                    'balance_start': statement.get('balance_start',False),
                    'balance_end_real': statement.get('balance_end_real',False),
                    'state': 'draft',
                    'name': statement.get('name',False),
                })
                lines = statement.get('bank_statement_line',False)
                if lines:
                    for value in lines:
                        journal = journal_obj.browse(cr, uid, statement['journal_id'], context=context)
                        line = lines[value]
                        if not line['partner_id']:
                            line['partner_id'] = journal.company_id.partner_id.id
                        voucher_id = False
                        rec_id = False
                        if line.get('toreconcile',False): # Fix me
                            name = line['name'][:3] + '/' + line['name'][3:7] + '/' + line['name'][7:]
                            rec_id = self.pool.get('account.move.line').search(cr, uid, [('name', '=', name), ('reconcile_id', '=', False), ('account_id.reconcile', '=', True)])
                            if rec_id:
                                result = voucher_obj.onchange_partner_id(cr, uid, [], partner_id=line['partner_id'], journal_id=statement['journal_id'], price=abs(line['amount']), currency_id = journal.company_id.currency_id.id, ttype=(line['amount'] < 0 and 'payment' or 'receipt'), context=context)
                                voucher_res = { 'type':(line['amount'] < 0 and 'payment' or 'receipt'),
                                'name': line['name'],#line.name,
                                'partner_id': line['partner_id'],#line.partner_id.id,
                                'journal_id': statement['journal_id'], #statement.journal_id.id,
                                'account_id': result.get('account_id', journal.default_credit_account_id.id),#line.account_id.id,
                                'company_id': journal.company_id.id,#statement.company_id.id,
                                'currency_id': journal.company_id.currency_id.id,#statement.currency.id,
                                'date': line['date'], #line.date,
                                'amount':abs(line['amount']),
                                'period_id':statement.get('period_id',False) or period,# statement.period_id.id
                                }
                                voucher_id = voucher_obj.create(cr, uid, voucher_res, context=context)
                                context.update({'move_line_ids': rec_id})

                                voucher_line_dict =  False
                                if result['value']['line_ids']:
                                    for line_dict in result['value']['line_ids']:
                                        move_line = line_obj.browse(cr, uid, line_dict['move_line_id'], context)
                                        if line.move_id.id == move_line.move_id.id:
                                            voucher_line_dict = line_dict

                                if voucher_line_dict:
                                    voucher_line_dict.update({'voucher_id':voucher_id})
                                    voucher_line_obj.create(cr, uid, voucher_line_dict, context=context)

        #                            reconcile_id = statement_reconcile_obj.create(cr, uid, {
        #                                'line_ids': [(6, 0, rec_id)]
        #                                }, context=context)
        #

                                mv = self.pool.get('account.move.line').browse(cr, uid, rec_id[0], context=context)
                                if mv.partner_id:
                                    line['partner_id'] = mv.partner_id.id
                                    if line['amount'] < 0:
                                        line['account_id'] = mv.partner_id.property_account_payable.id
                                    else:
                                        line['account_id'] = mv.partner_id.property_account_receivable.id
                        str_not1 = ''
                        if line.has_key('contry_name') and line.has_key('cntry_number'):
                            str_not1="Partner name:%s \n Partner Account Number:%s \n Communication:%s \n Value Date:%s \n Entry Date:%s \n"%(line["contry_name"], line["cntry_number"], line["free_comm"]+line['extra_note'], line["val_date"][0], line["entry_date"][0])
                        bank_statement_line_obj.create(cr, uid, {
                                   'name':line['name'],
                                   'date': line['date'],
                                   'amount': line['amount'],
                                   'partner_id':line['partner_id'],
                                   'account_id':line['account_id'],
                                   'statement_id': bk_st_id,
                                   'voucher_id': voucher_id,
                                   'note':str_not1,
                                   'ref':line['ref'],
                                   })

                str_not = "\n \n Account Number: %s \n Account Holder Name: %s " %(statement["acc_number"], statement["acc_holder"])
                std_log += "\nStatement: %s, Date: %s, Starting Balance:  %.2f, Ending Balance: %.2f \n"\
                          %(statement['name'], statement['date'], float(statement["balance_start"]), float(statement["balance_end_real"]))
                bkst_list.append(bk_st_id)

            except osv.except_osv, e:
                cr.rollback()
                nb_err += 1
                err_log += '\n Application Error: ' + str(e)
                raise # REMOVEME

            except Exception, e:
                cr.rollback()
                nb_err += 1
                err_log += '\n System Error: '+str(e)
                raise # REMOVEME
            except:
                cr.rollback()
                nb_err+=1
                err_log += '\n Unknown Error'
                raise
        err_log += '\n\nNumber of statements: '+ str(len(bkst_list))
        err_log += '\nNumber of error:'+ str(nb_err) +'\n'

        account_coda_obj.create(cr, uid, {
            'name': codafile,
            'statement_ids': [(6, 0, bkst_list,)],
            'note': str_log1+str_not+std_log+err_log,
            'journal_id': data.journal_id.id,
            'date': time.strftime("%Y-%m-%d"),
            'user_id': uid,
        })
        test = ''
        test = str_log1 + std_log + err_log
        self.write(cr, uid, ids, {'note': test}, context=context)
        context.update({ 'statment_ids': bkst_list})
        model_data_ids = mod_obj.search(cr, uid, [('model', '=', 'ir.ui.view'), ('name', '=', 'account_coda_note_view')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']

        return {
            'name': _('Result'),
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

    def action_open_window(self, cr, uid, data, context=None):
        if context is None:
            context = {}

        return {
            'domain':"[('id','in',%s)]"%(context.get('statment_ids', False)),
            'name': 'Statement',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.bank.statement',
            'view_id': False,
            'type': 'ir.actions.act_window',
    }

account_coda_import()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
