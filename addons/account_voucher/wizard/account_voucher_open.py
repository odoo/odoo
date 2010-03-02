# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
import netsvc
from osv import fields, osv
import ir
import pooler
import mx.DateTime
from mx.DateTime import RelativeDateTime
from tools import config

class account_voucher_open(osv.osv_memory):
    """
    Open Account Voucher
    """
    _name ="account.voucher.open"
    _description ="Open Voucher"
    _columns ={
               'type':fields.selection([('pay_voucher','Cash Payment Voucher'),('bank_pay_voucher','Bank Payment Voucher'),('rec_voucher','Cash Receipt Voucher'),('bank_rec_voucher','Bank Receipt Voucher'),('cont_voucher','Contra Voucher'),( 'journal_sale_vou','Journal Sale Voucher'),('journal_pur_voucher','Journal Purchase Voucher')], 'Voucher Type', required=True),
               'state':fields.selection([('draft','Draft'),
                                         ('proforma','Pro-forma'),
                                         ('posted','Posted'),
                                         ('cancel','Cancel')], 'State', required=True),
                'period_ids':fields.many2many('account.period', 'account_period_rel', 'voucher_id', 'period_id', 'Periods')                         
               }
    def _action_open_window(self, cr, uid, ids, context):
        """
        Open account voucher form.
        @param cr: the current row, from the database cursor.
        @param uid: the current user’s ID for security checks.
        @param id: account voucher open’s ID or list of IDs if we want more than one.
        @param return:dictionary of account voucher on  given state ,type and account period id.
         """
        
        for form  in self.read(cr, uid, ids):
            periods = []
            if not form['period_ids']:
                period = self.pool.get('account.period')
                year = self.pool.get('account.fiscalyear')
                year = year.find(cr, uid)
                periods = period.search(cr, uid, [('fiscalyear_id','=',year)])
            else:
                periods = form['period_ids']
        
            return {
                'domain': "[('type','=','%s'), ('state','=','%s'), ('period_id','in',%s)]" % (form['type'], form['state'], periods),
                'name': "%s - %s" % (form['type'],form['state']),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.voucher',
                'view_id': False,
                'context': "{'type':'%s', 'state':'%s', 'period_id':%s}" % (form['type'], form['state'], periods),
                'type': 'ir.actions.act_window'
                }
account_voucher_open()


