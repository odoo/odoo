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

invoice_form = '''<?xml version="1.0"?>
<form string="Pay invoice">
    <field name="amount"/>
    <field name="dest_account_id"/>
    <field name="journal_id"/>
    <field name="period_id"/>
</form>'''

invoice_fields = {
    'amount': {'string': 'Amount paid', 'type':'float', 'required':True},
    'dest_account_id': {'string':'Payment to Account', 'type':'many2one', 'required':True, 'relation':'account.account', 'domain':[('type','=','cash')]},
    'journal_id': {'string': 'Journal', 'type': 'many2one', 'relation':'account.journal', 'required':True},
    'period_id': {'string': 'Period', 'type': 'many2one', 'relation':'account.period', 'required':True},
}
#def pay_n_check(self, cr, uid, data, context):
#
#   auction = pool.get('auction.lots').browse(cr,uid,data['id'],context)
#   try:
#       
#       for lot in auction:
#                            
#           if not lot.auction_id :
#               raise osv.except_osv("Error","No payment defined for this auction.")
#           i=1
#           tot= 0
#           for payment in auction:
#               if not payment.journal_id :
#                   raise osv.except_osv("Error","No journal defined for the payment line %d" % (i,))
#               if not payment.ach_inv_id.amount :
#                   raise osv.except_osv("Error","No amount defined for the payment line %d." % (i,))
#               i+=1
#               tot+= payment.ach_inv_id.amount
#           if abs(float(tot)) - abs(float(lot.obj_ret)) > 10**-6:
#               raise osv.except_osv("Error","The amount paid does not match the total amount")
#       else:
#           for lot in auction:
#              if not lot.journal_id :
#               raise osv.except_osv("Error","Please choose a journal for the auction ("+lot.name+").")
#           pool.get('auction.lots').create(cr,uid,{
#               'auction_id': lot.auction.id,
#               'journal_id': lot.journal_id,
#
#               })
#   except osv.except_osv, e:
#       raise wizard.except_wizard(e.name, e.name)
#   return True
def _pay_and_reconcile(self, cr, uid, data, context):

    pool = pooler.get_pool(cr.dbname)
    lot = pool.get('auction.lots').browse(cr,uid,data['id'],context)
    form = data['form']
    account_id = form.get('writeoff_acc_id', False)
    period_id = form.get('period_id', False)
    journal_id = form.get('journal_id', False)
    if lot.sel_inv_id:
        p=pool.get('account.invoice').pay_and_reconcile(['lot.sel_inv_id.id'], form['amount'], form['dest_account_id'], journal_id, account_id, period_id, journal_id, context)
#   lots.sel_inv_id.pay_and_reconcile(cr,uid,data[id], form['amount'], form['dest_account_id'], journal_id, account_id, period_id, journal_id, context)
    return {}


class wiz_auc_lots_pay(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':invoice_form, 'fields': invoice_fields, 'state':[ ('pay','Pay'), ('end','Cancel')]}
        },
            'pay': {
            'actions': [_pay_and_reconcile],
            'result': {'type': 'state', 'state':'end'}
        }}
wiz_auc_lots_pay('auction.pay.sel');


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

