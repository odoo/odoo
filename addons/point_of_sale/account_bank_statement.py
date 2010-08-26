# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
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
from osv import osv
from osv import fields
from mx import DateTime
from decimal import Decimal
from tools.translate import _

class account_journal(osv.osv):

    _inherit = 'account.journal'
    _columns = {
        'auto_cash': fields.boolean('Automatic Opening', help="This field authorize the automatic creation of the cashbox"),
        'special_journal':fields.boolean('Special Journal', help="Will put all the orders in waiting status till being accepted"),
        'check_dtls': fields.boolean('Check Details', help="This field authorize Validation of Cashbox without checking ending details"),
        'journal_users': fields.many2many('res.users','pos_journal_users','journal_id','user_id','Users'),
    }
    _defaults = {
        'check_dtls': lambda *a:False,
        'auto_cash': lambda *a:True,
    }
account_journal()

class account_cash_statement(osv.osv):
    
    _inherit = 'account.bank.statement'

    def _equal_balance(self, cr, uid, ids, statement, context={}):

        if not statement.journal_id.check_dtls:
            return True
        
        if statement.journal_id.check_dtls and (statement.balance_end != statement.balance_end_cash):
            return False
        else:
            return True            
    
    def _user_allow(self, cr, uid, ids, statement, context={}):
        res = False
        uids = []
        for user in statement.journal_id.journal_users:
            uids.append(user.id)
        
        if uid in uids:
            res = True
      
        return res
    
account_cash_statement()

class account_bank_statement_line(osv.osv):
    
    def _default_company(self, cr, uid, context={}):
        """ To get default company for the object"
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of bank statement ids
        @param context: A standard dictionary for contextual values 
        @return: company 
        """          
        
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            return user.company_id.id
        
        return self.pool.get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]
    
    _inherit = 'account.bank.statement.line'
    _columns = {
        'company_id':fields.many2one('res.company', 'Company', required=True),
    }
    _defaults = {
        'company_id': _default_company,
    }
account_bank_statement_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
