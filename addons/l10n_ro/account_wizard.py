# -*- encoding: utf-8 -*-
##############################################################################
#
#     Author: Tatár Attila <atta@nvm.ro>
#    Copyright (C) 2011-2014 TOTAL PC SYSTEMS (http://www.erpsystems.ro). 
#    Copyright (C) 2014 Tatár Attila
#     Based on precedent versions developed by Fil System, Mihai Fekete
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
from openerp.osv import osv

class wizard_multi_charts_accounts(osv.TransientModel):
    
    _inherit = 'wizard.multi.charts.accounts'
    
    def execute(self, cr, uid, ids, context=None):
        """ from account/account.py ~ln 3398 """
        
        res = super(wizard_multi_charts_accounts, self).execute(cr, uid, ids,
                                                                context=context)        
        jou_obj = self.pool.get('account.journal') 
        seq_obj = self.pool.get('ir.sequence')       
        journal_ids = jou_obj.search(cr, uid,[]) 
        for j_o in jou_obj.browse(cr,uid,journal_ids):
            if j_o.type=='sale' and j_o.code=='SAJ':
                crt = self.pool.get('account.account').search(
                          cr, uid, [('code','like','4111')])[0]
                dbt = self.pool.get('account.account').search(
                          cr, uid, [('code','like','7070')])[0]
                jou_obj.write(cr, uid, j_o.id,{
                                    'code':'VMARF',
                                    'name':u'Vânzări marfă',
                                    'default_credit_account_id': dbt,
                                    'default_debit_account_id':  crt,
                                    'allow_date':True })
                seq_id = j_o.sequence_id.id 
                seq_obj.write(cr, uid, seq_id,{'prefix':'VMARF/%(year)s/',
                                        'name':u'Serie jurnal vânzări marfă'})
            if j_o.type=='purchase' and j_o.code=='EXJ':
                crt = self.pool.get('account.account').search(
                          cr, uid, [('code','like','371')])[0]
                dbt = self.pool.get('account.account').search(
                          cr, uid, [('code','like','401')])[0]
                jou_obj.write(cr, uid, j_o.id,{
                                    'code':'AMARF',
                                    'name':u'Achiziţii marfă',
                                    'default_credit_account_id': dbt,
                                    'default_debit_account_id':  crt,
                                    'allow_date':True })
                seq_id = j_o.sequence_id.id 
                seq_obj.write(cr, uid, seq_id,{
                                    'prefix':'AMARF/%(year)s/',
                                    'name':u'Serie jurnal achiziţii marfă' })
            if j_o.type=='general' and j_o.code=='MISC':
                dbt = self.pool.get('account.account').search(
                          cr, uid, [('code','like','1210')])[0]
                crt = dbt
                jou_obj.write(cr, uid, j_o.id,{
                                    'code':'DIVER',
                                    'name':'Jurnal diverse',
                                    'default_credit_account_id': dbt,
                                    'default_debit_account_id':  crt,
                                    'allow_date':True })
                seq_id = j_o.sequence_id.id 
                seq_obj.write(cr, uid, seq_id,{
                                    'prefix':'DIVER/%(year)s/',
                                    'name':'Serie jurnal diverse' })
            if j_o.type=='situation' and j_o.code=='OPEJ':
                dbt = self.pool.get('account.account').search(
                          cr, uid, [('code','like','4730')])[0]
                crt = dbt
                jou_obj.write(cr, uid, j_o.id,{
                                    'code':'DESCH',
                                    'name':u'înregistrări de deschidere',
                                    'default_credit_account_id': dbt,
                                    'default_debit_account_id':  crt,
                                    'allow_date':False })
                seq_id = j_o.sequence_id.id 
                seq_obj.write(cr, uid, seq_id,{
                                    'prefix':'DESCH/%(year)s/',
                                    'name':'Serie jurnal deschidere' })
            if j_o.type=='cash' and j_o.code=='BNK1':
                dbt = self.pool.get('account.account').search(
                          cr, uid, [('code','like','5311')])[0]
                crt = dbt
                jou_obj.write(cr, uid, j_o.id,{
                                    'code':'CASA1',
                                    'name':'Numerar casa 1',
                                    'default_credit_account_id': dbt,
                                    'default_debit_account_id':  crt,
                                    'allow_date':True,
                                    'with_last_closing_balance':True,
                                    'cash_control':True })
                seq_id = j_o.sequence_id.id 
                seq_obj.write(cr, uid, seq_id,{
                                    'prefix':'CASA1/%(year)s/',
                                    'name':'Serie jurnal numerar casa 1' })
            if j_o.type=='bank' and j_o.code=='BNK2':
                dbt = self.pool.get('account.account').search(
                          cr, uid, [('code','like','5121')])[0]
                crt = dbt
                jou_obj.write(cr, uid, j_o.id,{
                                    'code':'BNC1',
                                    'name':'Banca 1',
                                    'default_credit_account_id': dbt,
                                    'default_debit_account_id':  crt,
                                    'allow_date':True })
                seq_id = j_o.sequence_id.id 
                seq_obj.write(cr, uid, seq_id,{
                                    'prefix':'BANC1/%(year)s/',
                                    'name':'Serie jurnal banca 1' })
        unlink_ids = jou_obj.search(cr, uid,['|',
                                             ('code','=','SCNJ'),
                                             ('code','=','ECNJ')
                                             ])
        jou_obj.unlink(cr, uid, unlink_ids)
        return res
