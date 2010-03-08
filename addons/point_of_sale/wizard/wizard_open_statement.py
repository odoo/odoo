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

import pooler
import wizard
from tools.translate import _
import time

statement_form = """<?xml version="1.0"?>
<form string="Open Statements">
     <label string="Are you sure you want to open the statements ?" colspan="2"/>
</form>
"""
statement_form_close = """<?xml version="1.0"?>
<form string="Close Statements">
     <label string="Are you sure you want to close the statements ?" colspan="2"/>
</form>
"""

statement_fields = {}

def _close_statement(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    company_id=pool.get('res.users').browse(cr,uid,uid).company_id.id
    statement_obj = pool.get('account.bank.statement')
    singer_obj = pool.get('singer.statement')
    journal_obj=pool.get('account.journal')
    journal_lst=journal_obj.search(cr,uid,[('company_id','=',company_id),('auto_cash','=',True),('check_dtls','=',False)])
    journal_ids=journal_obj.browse(cr,uid, journal_lst)
    for journal in journal_ids:
        ids = statement_obj.search(cr, uid, [('state','!=','confirm'),('user_id','=',uid),('journal_id','=',journal.id)])
        statement_obj.button_confirm(cr,uid,ids)
    return {}
def _open_statement(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    company_id=pool.get('res.users').browse(cr,uid,uid).company_id.id
    statement_obj = pool.get('account.bank.statement')
    singer_obj = pool.get('singer.statement')
    journal_obj=pool.get('account.journal')
    journal_lst=journal_obj.search(cr,uid,[('company_id','=',company_id),('auto_cash','=',True)])
    journal_ids=journal_obj.browse(cr,uid, journal_lst)
    for journal in journal_ids:
        ids = statement_obj.search(cr, uid, [('state','!=','confirm'),('user_id','=',uid),('journal_id','=',journal.id)])
        if len(ids):
            raise wizard.except_wizard(_('Message'),_('You can not open a Cashbox for "%s". \n Please close the cashbox related to. '%(journal.name) ))
        sql = """ Select id from account_bank_statement
                                where journal_id=%d
                                and company_id =%d
                                order by id desc limit 1"""%(journal.id,company_id)
        singer_ids=None
        cr.execute(sql)
        st_id = cr.fetchone()
        number=''
        if journal.statement_sequence_id:
            number = pool.get('ir.sequence').get_id(cr, uid, journal.id)
        else:
            number = pool.get('ir.sequence').get(cr, uid,
                            'account.bank.statement')

#        statement_id=statement_obj.create(cr,uid,{'journal_id':journal.id,
#                                                  'company_id':company_id,
#                                                  'user_id':uid,
#                                                  'state':'open',
#                                                  'name':number
#                                                  })
        period=statement_obj._get_period(cr,uid,context) or None
        cr.execute("INSERT INTO account_bank_statement(journal_id,company_id,user_id,state,name, period_id,date) VALUES(%d,%d,%d,'open','%s',%d,'%s')"%(journal.id,company_id,uid,number, period, time.strftime('%Y-%m-%d %H:%M:%S')))
        cr.commit()
        cr.execute("select id from account_bank_statement where journal_id=%d and company_id=%d and user_id=%d and state='open' and name='%s'"%(journal.id,company_id,uid,number))
        statement_id=cr.fetchone()[0]
        if st_id:
            statemt_id=statement_obj.browse(cr,uid,st_id[0])
            if statemt_id and statemt_id.ending_details_ids:
                statement_obj.write(cr, uid,[statement_id], {'balance_start':statemt_id.balance_end,
                                                            'state':'open'})
                if statemt_id.ending_details_ids:
                    for i in statemt_id.ending_details_ids:
                        c=singer_obj.create(cr,uid, { 'pieces':i.pieces,
                                                    'number':i.number,
                                                    'starting_id':statement_id,
                            })
        cr.commit()
    return {}

class statement_open(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': statement_form,
                'fields': statement_fields,
                'state': (('end', 'No','gtk-cancel'),
                          ('open', 'Yes', 'gtk-ok', True)
                         )
            }
        },
        'open': {
            'actions': [_open_statement],
            'result': {
                       'type': 'state',
#                       'action' :_open_statement,
                       'state':'end'}
        },
    }
statement_open('statement.open')
class statement_close(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': statement_form_close,
                'fields': statement_fields,
                'state': (('end', 'No','gtk-cancel'),
                          ('open', 'Yes', 'gtk-ok', True)
                         )
            }
        },
        'open': {
            'actions': [_close_statement],
            'result': {
                       'type': 'state',
                       'state':'end'}
        },
    }
statement_close('statement.close')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
