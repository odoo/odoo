# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


import time
import netsvc
from tools.misc import UpdateableStr
import wizard
import pooler
from mx import DateTime
from tools.translate import _


entry_form = '''<?xml version="1.0"?>
<form string="%s">
<separator string="Please fill these fields for entries to the box:" colspan="4"/>
<newline/>
<field name="name"/>
<field name="ref"/>
<field name="journal_id"/>
<field name="amount"/>
<field name="product_id"/>
</form>
'''

def _get_journal(self,cr,uid,context):
    pool = pooler.get_pool(cr.dbname)
    obj = pool.get('account.journal')
    user = pool.get('res.users').browse(cr, uid, uid)
    ids = obj.search(cr, uid, [('type', '=', 'cash'), ('company_id', '=', user.company_id.id)])
    res = obj.read(cr, uid, ids, ['id', 'name'], context)
    res = [(r['id'], r['name']) for r in res]
    res.insert(0, ('', ''))
    return res

def _get_pdt(self,cr,uid,context):
    pool = pooler.get_pool(cr.dbname)
    obj = pool.get('product.product')
    ids = obj.search(cr, uid, [('income_pdt', '=', True)])
    res = obj.read(cr, uid, ids, ['id', 'name'], context)
    res = [(r['id'], r['name']) for r in res]
    res.insert(0, ('', ''))
    return res

def _get_pdt_exp(self,cr,uid,context):
    pool = pooler.get_pool(cr.dbname)
    obj = pool.get('product.product')
    company_id = pool.get('res.users').browse(cr, uid, uid).company_id.id
    ids = obj.search(cr, uid, ['&', ('expense_pdt', '=', True), '|', ('company_id', '=', company_id), ('company_id', '=', None)])
    res = obj.read(cr, uid, ids, ['id', 'name'], context)
    res = [(r['id'], r['name']) for r in res]
    res.insert(0, ('', ''))
    return res

entry_fields = {
    'journal_id': {'string': 'Journal', 'type': 'selection', 'selection': _get_journal, 'required':True},
    'product_id': {'string': 'Operation', 'type': 'selection', 'selection':_get_pdt , 'required':True},
    'amount': {'string': 'Amount', 'type': 'float'},
    'name': {'string': 'Name', 'type': 'char', 'size': '32', 'required':True},
    'ref': {'string': 'Ref.', 'type': 'char', 'size': '32'},

}

out_fields = {
    'journal_id': {'string': 'Journal', 'type': 'selection', 'selection': _get_journal, 'required':True},
    'product_id': {'string': 'Operation', 'type': 'selection', 'selection':_get_pdt_exp , 'required':True},
    'amount': {'string': 'Amount', 'type': 'float'},
    'name': {'string': 'Name', 'type': 'char', 'size': '32', 'required':True},
    'ref': {'string': 'Ref.', 'type': 'char', 'size': '32'},
}

def _get_out(self, cr, uid, data, context):
    args = {}
    pool = pooler.get_pool(cr.dbname)
    statement_obj= pool.get('account.bank.statement')
    product_obj= pool.get('product.template')
    productp_obj= pool.get('product.product')
    res_obj = pool.get('res.users')
    curr_company = res_obj.browse(cr,uid,uid).company_id.id
    statement_id = statement_obj.search(cr,uid, [('journal_id','=',data['form']['journal_id']),('company_id','=',curr_company),('user_id','=',uid),('state','=','open')])
    monday = (DateTime.now() + DateTime.RelativeDateTime(weekday=(DateTime.Monday,0))).strftime('%Y-%m-%d')
    sunday = (DateTime.now() + DateTime.RelativeDateTime(weekday=(DateTime.Sunday,0))).strftime('%Y-%m-%d')
    done_statmt = statement_obj.search(cr,uid, [('date','>=',monday+' 00:00:00'),('date','<=',sunday+' 23:59:59'),('journal_id','=',data['form']['journal_id']),('company_id','=',curr_company),('user_id','=',uid)])
    stat_done = statement_obj.browse(cr,uid, done_statmt)
    address_u = pool.get('res.users').browse(cr,uid,uid).address_id
    am = 0.0
    amount_check = productp_obj.browse(cr,uid,data['form']['product_id']).am_out or False
    for st in stat_done:
        for s in st.line_ids:
            if address_u and s.partner_id==address_u.partner_id and s.am_out:
                am+=s.amount
    if (-data['form']['amount'] or 0.0)+ am <-(res_obj.browse(cr,uid,uid).company_id.max_diff or 0.0) and amount_check:
        val = (res_obj.browse(cr,uid,uid).company_id.max_diff or 0.0)+ am
        raise wizard.except_wizard(_('Error !'), _('The maximum value you can still withdraw is exceeded. \n Remaining value is equal to %d ')%(val))

    acc_id = product_obj.browse(cr,uid,data['form']['product_id']).property_account_income
    if not acc_id:
        raise wizard.except_wizard(_('Error !'), _('please check that account is set to %s')%(product_obj.browse(cr,uid,data['form']['product_id']).name))
    if not statement_id:
        raise wizard.except_wizard(_('Error !'), _('You have to open at least one cashbox'))
    if statement_id:
        statement_id = statement_id[0]
    if not statement_id:
        statement_id = statement_obj.create(cr,uid,{'date':time.strftime('%Y-%m-%d 00:00:00'),
                                        'journal_id':data['form']['journal_id'],
                                        'company_id':curr_company,
                                        'user_id':uid,
                                        })
    args['statement_id']= statement_id
    args['journal_id']= data['form']['journal_id']
    if acc_id:
        args['account_id']= acc_id.id
    amount= data['form']['amount'] or 0.0
    if data['form']['amount'] > 0:
        amount= -data['form']['amount']
    args['amount'] = amount
    if productp_obj.browse(cr,uid,data['form']['product_id']).am_out:
        args['am_out'] = True
    args['ref'] = data['form']['ref'] or ''
    args['name'] = "%s: %s "%(product_obj.browse(cr,uid,data['form']['product_id']).name, data['form']['name'].decode('utf8'))
    address_u = pool.get('res.users').browse(cr,uid,uid).address_id
    if address_u:
        partner_id = address_u.partner_id and address_u.partner_id.id or None
        args['partner_id'] = partner_id
    statement_line_id = pool.get('account.bank.statement.line').create(cr, uid, args)
    return {}

def _get_in(self, cr, uid, data, context):
    args = {}
    pool = pooler.get_pool(cr.dbname)
    statement_obj = pool.get('account.bank.statement')
    product_obj = pool.get('product.template')
    res_obj = pool.get('res.users')
    curr_company = res_obj.browse(cr,uid,uid).company_id.id
    statement_id = statement_obj.search(cr,uid, [('journal_id','=',data['form']['journal_id']),('company_id','=',curr_company),('user_id','=',uid),('state','=','open')])
    if not statement_id:
        raise wizard.except_wizard(_('Error !'), _('You have to open at least one cashbox'))

    product = pool.get('product.product').browse(cr, uid, data['form']['product_id'])
    acc_id = product_obj.browse(cr,uid,data['form']['product_id']).property_account_income
    if not acc_id:
        raise wizard.except_wizard(_('Error !'), _('please check that account is set to %s')%(product_obj.browse(cr,uid,data['form']['product_id']).name))
    if statement_id:
        statement_id = statement_id[0]
    if not statement_id:
        statement_id = statement_obj.create(cr,uid,{'date':time.strftime('%Y-%m-%d 00:00:00'),
                                                    'journal_id':data['form']['journal_id'],
                                                    'company_id':curr_company,
                                                    'user_id':uid,
                                                   })

    args['statement_id'] = statement_id
    args['journal_id'] =  data['form']['journal_id']
    if acc_id:
        args['account_id'] =  acc_id.id
    args['amount'] = data['form']['amount'] or 0.0
    args['ref'] = "%s" %(data['form']['ref'] or '')
    args['name'] = "%s: %s "% (product_obj.browse(cr,uid,data['form']['product_id']).name, data['form']['name'].decode('utf8'))
    address_u = pool.get('res.users').browse(cr,uid,uid).address_id
    if address_u:
        partner_id = address_u.partner_id and address_u.partner_id.id or None
        args['partner_id'] = partner_id
    statement_line_id = pool.get('account.bank.statement.line').create(cr, uid, args)

    return {}

class box_entries(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': entry_form % u'Entrée de caisse',
                'fields': entry_fields,
                'state': [('end', 'Cancel', 'gtk-cancel'), ('next', 'Make entries in the Cashbox', 'gtk-ok')]
            }
        },
        'next': {
            'actions': [],
            'result': {
                'type': 'action',
                'action': _get_in,
                'state': 'end'
            }
        },
    }

box_entries('pos.entry')

class box_out(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': entry_form % u'Sortie de caisse',
                'fields': out_fields,
                'state': [('end', 'Cancel', 'gtk-cancel'), ('next', 'Make Entries in the CashBox', 'gtk-ok')]
            }
        },
        'next': {
            'actions': [],
            'result': {
                'type': 'action',
                'action': _get_out,
                'state': 'end'
            }
        },
    }

box_out('pos.out')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

