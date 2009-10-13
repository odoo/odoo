# -*- coding: utf-8 -*-
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

import wizard
import netsvc
import netsvc
import osv
import time
import pooler
pay_form = '''<?xml version="1.0"?>
<form string="Pay objects">
    <field name="amount"/>
    <field name="statement_id1" domain="[('state','=','draft')]"/>
    <field name="amount2"/>
    <field name="statement_id2"  domain="[('state','=','draft')]"/>
    <field name="amount3"/>
    <field name="statement_id3"  domain="[('state','=','draft')]"/>
    <newline/>
    <field name="buyer_id"/>
    <field name="total"/>
</form>'''

def _start(self,cr,uid,data,context):
    pool = pooler.get_pool(cr.dbname)
    rec=pool.get('auction.lots').browse(cr,uid,data['ids'],context)
    amount1=0.0
    for r in rec:
        amount1+=r.buyer_price
        buyer= r and r.ach_uid.id or False
        if r.is_ok:
            raise wizard.except_wizard('Error !', 'Some lots of the selection are already paid.')
    return {'amount':amount1, 'total':amount1,'buyer_id':buyer}

pay_fields = {
    'amount': {'string': 'Amount paid', 'type':'float'},
    'buyer_id': {'string': 'Buyer', 'type': 'many2one', 'relation':'res.partner'},
    'statement_id1': {'string':'Statement', 'type':'many2one', 'required':True, 'relation':'account.bank.statement'},
    'amount2': {'string': 'Amount paid', 'type':'float'},
    'statement_id2': {'string':'Statement', 'type':'many2one', 'relation':'account.bank.statement'},
    'amount3': {'string': 'Amount paid', 'type':'float'},
    'statement_id3': {'string':'Statement', 'type':'many2one', 'relation':'account.bank.statement'},
    'total': {'string': 'Amount to paid', 'type':'float','readonly':True}
}

def _pay_and_reconcile(self, cr, uid, data, context):
    if not abs(data['form']['total'] - (data['form']['amount']+data['form']['amount2']+data['form']['amount3']))<0.01:
        rest=data['form']['total']-(data['form']['amount']+data['form']['amount2']+data['form']['amount3'])
        raise wizard.except_wizard('Payment aborted !', 'You should pay all the total: "%.2f" are missing to accomplish the payment.' %(round(rest,2)))
    
    pool = pooler.get_pool(cr.dbname)
    lots = pool.get('auction.lots').browse(cr,uid,data['ids'],context)
    ref_bk_s=pooler.get_pool(cr.dbname).get('account.bank.statement.line')
    
    for lot in lots:
        if data['form']['buyer_id']:
            pool.get('auction.lots').write(cr,uid,[lot.id],{'ach_uid':data['form']['buyer_id']})
        if not lot.auction_id:
            raise wizard.except_wizard('Error !', 'No auction date for "%s": Please set one.'%(lot.name))
        pool.get('auction.lots').write(cr,uid,[lot.id],{'is_ok':True})
    
    for st,stamount in [('statement_id1','amount'),('statement_id2','amount2'),('statement_id3','amount3')]:
        if data['form'][st]:
            new_id=ref_bk_s.create(cr,uid,{
                'name':'Buyer:'+str(lot.ach_login or '')+', auction:'+ lots[0].auction_id.name,
                'date': time.strftime('%Y-%m-%d'),
                'partner_id':data['form']['buyer_id'] or False,
                'type':'customer',
                'statement_id':data['form'][st],
                'account_id':lot.auction_id.acc_income.id,
                'amount':data['form'][stamount]
            })
            for lot in lots:
                pool.get('auction.lots').write(cr,uid,[lot.id],{'statement_id':[(4,new_id)]})
    return {}


class wiz_auc_lots_pay(wizard.interface):
    states = {
        'init': {
            'actions': [_start],
            'result': {'type': 'form', 'arch':pay_form, 'fields': pay_fields, 'state':[('end','Cancel'),('pay','Pay')]}
        },
        'pay': {
        'actions': [_pay_and_reconcile],
        'result': {'type': 'state', 'state':'end'}
        }}
wiz_auc_lots_pay('auction.pay.buy')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

