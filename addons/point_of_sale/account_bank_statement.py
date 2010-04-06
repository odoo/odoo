# encoding: utf-8
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
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

from osv import osv, fields
import time
from mx import DateTime
from decimal import Decimal
from tools.translate import _


class account_journal(osv.osv):

    _inherit = 'account.journal'
    _columns = {
        'auto_cash': fields.boolean('Automatic Opening', help="This field authorize the automatic creation of the cashbox"),
        'special_journal':fields.boolean('Special Journal', help="Will put all the orders in waiting status till being accepted"),
        'check_dtls': fields.boolean('Check Details', help="This field authorize Validation of Cashbox without checking ending details"),
        'statement_sequence_id': fields.many2one('ir.sequence', 'Statement Sequence', \
            help="The sequence used for statement numbers in this journal."),
        }
    _defaults = {
        'check_dtls': lambda *a:True,
        'auto_cash': lambda *a:True,
        }
account_journal()


class singer_statement(osv.osv):
    
    """ Singer Statements """
    
    _name = 'singer.statement'
    _description = 'Statements'

    def _sub_total(self, cr, uid, ids, name, arg, context=None):
       
        """ Calculates Sub total"
        @param name: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """
        res = {}
        for obj in self.browse(cr, uid, ids):
            res[obj.id] = obj.pieces * obj.number
        return res

    def on_change_sub(self, cr, uid, ids, pieces, number,*a):

        """ Calculates Sub total on change of number"
        @param pieces: Names of fields.
        @param number:
        @param *a: User defined arguments
        @return: Dictionary of values.
        """           
        sub=pieces*number
        return {'value':{'subtotal': sub or 0.0}}

    _columns = {
          'pieces': fields.float('Values', digits=(16,2)),
          'number': fields.integer('Number'),
          'subtotal': fields.function(_sub_total, method=True, string='Sub Total', type='float',digits=(16,2)),
          'starting_id': fields.many2one('account.bank.statement',ondelete='cascade'),
          'ending_id': fields.many2one('account.bank.statement',ondelete='cascade'),
     }

singer_statement()

class account_bank_statement(osv.osv):
    
    _inherit = 'account.bank.statement'
    
    def _get_starting_balance(self, cr, uid, ids, name, arg, context=None):

        """ Find starting balance  "
        @param name: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """          
        res ={}
        for statement in self.browse(cr, uid, ids):
            amount_total=0.0
            for line in statement.starting_details_ids:
                amount_total+= line.pieces * line.number
            res[statement.id]=amount_total
        return res

    def _get_sum_entry_encoding(self, cr, uid, ids, name, arg, context=None):

        """ Find encoding total of statements "
        @param name: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """              
        res2={}
        for statement in self.browse(cr, uid, ids):
            encoding_total=0.0
            for line in statement.line_ids:
               encoding_total+= line.amount
            res2[statement.id]=encoding_total
        return res2

    def _default_journal_id(self, cr, uid, context={}):

        """ To get default journal for the object" 
        @param name: Names of fields.
        @return: journal 
        """  
        company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
        journal = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'cash'), ('auto_cash','=',False), ('company_id', '=', company_id)])
        if journal:
            return journal[0]
        else:
            return False

    _columns = {
          'journal_id': fields.many2one('account.journal', 'Journal', required=True),
          'balance_start': fields.function(_get_starting_balance, method=True, string='Starting Balance', type='float',digits=(16,2)),
         # 'balance_start': fields.float('Starting Balance',digits=(16,2)),
         # 'balance_end': fields.float('Balance',digits=(16,2)),
          'state': fields.selection([('draft', 'Draft'),('confirm', 'Confirm'),('open','Open')],
                                    'State', required=True, states={'confirm': [('readonly', True)]}, readonly="1"),
          'total_entry_encoding':fields.function(_get_sum_entry_encoding, method=True, string="Total of Entry encoding"),
          'date':fields.datetime("Opening Date"),
          'closing_date':fields.datetime("Closing Date"),
          'starting_details_ids': fields.one2many('singer.statement', 'starting_id', string='Starting Details'),
          'ending_details_ids': fields.one2many('singer.statement', 'ending_id', string='Ending Details'),
          'name': fields.char('Name', size=64, required=True, readonly=True),

    }
    _defaults = {
          'state': lambda *a: 'draft',
          'name': lambda *a: '/',
          'date': lambda *a:time.strftime("%Y-%m-%d %H:%M:%S"),
          'journal_id': _default_journal_id,

         }

    def create(self, cr, uid, vals, context=None):
        
        company_id = vals and vals.get('company_id',False)
        if company_id:
            open_jrnl = self.search(cr, uid, [('company_id', '=', vals['company_id']), ('journal_id', '=', vals['journal_id']), ('state', '=', 'open')])
            if open_jrnl:
                raise osv.except_osv('Error', u'Une caisse de type espèce est déjà ouverte')
            if 'starting_details_ids' in vals:
                vals['starting_details_ids'] = starting_details_ids = map(list, vals['starting_details_ids'])
                for i in starting_details_ids:
                    if i and i[0] and i[1]:
                        i[0], i[1] = 0, 0
        res = super(account_bank_statement, self).create(cr, uid, vals, context=context)
        return res

    def onchange_journal_id(self, cursor, user, statement_id, journal_id, context=None):
        
        """ Changes balance start and starting details if journal_id changes" 
        @param statement_id: Changed statement_id
        @param journal_id: Changed journal_id
        @return:  Dictionary of changed values
        """  
        id_s=[]
        if not journal_id:
            return {'value': {'balance_start': 0.0}}
        balance_start=0.0
        cash_obj = self.pool.get('singer.statement')
        statement_obj = self.pool.get('account.bank.statement')
        cursor.execute("Select a.id from account_bank_statement a where journal_id=%d and user_id=%d order by a.id desc limit 1"%(journal_id,user))
        res2=cursor.fetchone()
        res2=res2 and res2[0] or None
        if res2:
            statmt_id=statement_obj.browse(cursor,user,res2)
            check_det=statmt_id.journal_id.check_dtls
            if not check_det:
                balance_start=statmt_id.balance_end_real or 0.0
                return {'value': {'balance_start': balance_start}}
        cursor.execute("Select a.id from account_bank_statement a, singer_statement s where journal_id=%d and user_id=%d order by a.id desc limit 1"%(journal_id,user))
        res1=cursor.fetchone()
        res1=res1 and res1[0] or None
        if res1:
            cursor.execute("Select sum(ss.pieces*ss.number),ss.ending_id from singer_statement ss, account_bank_statement s where ss.ending_id=s.id and s.journal_id=%d and s.user_id=%d and s.id=%d group by ss.ending_id,s.id order by s.id desc"%(journal_id,user, res1))
            res = cursor.fetchone()
            balance_start = res and res[0] or 0.0
            cash_end=res and res[1] or None
            id_s=statement_obj.browse(cursor,user,cash_end).ending_details_ids
        new=[]
        if id_s:
            for s in id_s:
                new.append(s.id)
        return {'value': {'balance_start': balance_start, 'starting_details_ids':new}}

    def button_open(self, cr, uid, ids, context=None):
        """ Changes statement state to Running.
        @return: True 
        """       
        obj_inv = self.browse(cr, uid, ids)[0]
        s_id=obj_inv.journal_id
        if s_id.statement_sequence_id:
            s_id=s_id.id
            number = self.pool.get('ir.sequence').get_id(cr, uid, s_id)
        else:
            number = self.pool.get('ir.sequence').get(cr, uid,
                            'account.bank.statement')

        self.write(cr, uid, ids, {'date':time.strftime("%Y-%m-%d %H:%M:%S"), 'state':'open', 'name':number})
        return True

    def button_confirm(self, cr, uid, ids, context=None):
        
        """ Check the starting and ending detail of  statement 
        @return: True 
        """         
        val = 0.0
        val2 = 0.0
        val_statement_line = 0.0
        diff = self.pool.get('res.users').browse(cr,uid,uid).company_id.max_diff or 0.0
        for statement in self.browse(cr, uid, ids):
            bal = statement.balance_end
            bal_st=statement.balance_start
            for st in statement.line_ids:
                val_statement_line += st.amount
            for stat in statement.starting_details_ids:
                val2 += stat.subtotal
            for stat in statement.ending_details_ids:
                val += stat.subtotal
            if statement.journal_id.check_dtls:
                if Decimal(str(val)).quantize(Decimal('.001')) != (Decimal(str(val_statement_line)) + Decimal(str(val2))).quantize(Decimal('.001')):
                    raise osv.except_osv(_('Invalid action !'), _(' You can not confirm your cashbox, Please enter ending details, missing value matches to "%s"')%(abs(Decimal(str(val))-(Decimal(str(val_statement_line))+Decimal(str(val2))))))

            self.write(cr, uid, statement.id, {'balance_end_real':Decimal(str(val_statement_line))+Decimal(str(val2)),'closing_date':time.strftime("%Y-%m-%d %H:%M:%S"),'state':'draft'})
           # self.write(cr, uid, statement.id, {'balance_end_real':bal_st+val_statement_line,'closing_date':time.strftime("%Y-%m-%d %H:%M:%S"),'state':'draft'})
        return  super(account_bank_statement, self).button_confirm(cr, uid, ids, context=None)

account_bank_statement()

#class singer_account_bank_statement_line(osv.osv):
#    _inherit = 'account.bank.statement.line'
#    _columns = {
#           'pos_statement_id': fields.many2one('pos.order',ondelete='cascade'),
#     }
#
#singer_account_bank_statement_line()


