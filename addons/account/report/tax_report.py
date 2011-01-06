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
import pooler
import rml_parse
import copy
from report import report_sxw
import pdb
import re

class tax_report(rml_parse.rml_parse):
	_name = 'report.account.vat.declaration'
	def __init__(self, cr, uid, name, context):
		super(tax_report, self).__init__(cr, uid, name, context=context)
		self.localcontext.update({
			'time': time,
			'get_period': self._get_period,
			'get_codes': self._get_codes,
			'get_general': self._get_general,
			'get_company': self._get_company,
			'get_currency': self._get_currency,
			'get_lines' : self._get_lines,
		})

		
	def _get_lines(self, based_on,period_list,company_id=False, parent=False, level=0):
		res = self._get_codes(based_on,company_id,parent,level,period_list)
		
		if period_list[0][2] :
			res = self._add_codes(based_on,res,period_list)
		else :
			self.cr.execute ("select id from account_fiscalyear")
			fy = self.cr.fetchall()
			self.cr.execute ("select id from account_period where fiscalyear_id = %d"%(fy[0][0]))
			periods = self.cr.fetchall()
			for p in periods :
				period_list[0][2].append(p[0])
			res = self._add_codes(based_on,res,period_list)
		
		i = 0
		top_result = []
		while i < len(res):
			
			res_dict = { 'code' : res[i][1].code,
				'name' : res[i][1].name,
				'debit' : 0,
				'credit' : 0,
				'tax_amount' : res[i][1].sum_period,
				'type' : 1,
				'level' : res[i][0],
				'pos' : 0
			}
			
			top_result.append(res_dict)
			res_general = self._get_general(res[i][1].id,period_list,company_id,based_on)
			ind_general = 0
			while ind_general < len(res_general) :
				res_general[ind_general]['type'] = 2
				res_general[ind_general]['pos'] = 0
				res_general[ind_general]['level'] = res_dict['level']
				top_result.append(res_general[ind_general])
				ind_general+=1
			i+=1
		#array_result = self.sort_result(top_result)
		return top_result
		#return array_result

	def _get_period(self, period_id):
		return self.pool.get('account.period').browse(self.cr, self.uid, period_id).name

	def _get_general(self, tax_code_id,period_list ,company_id, based_on):
		res=[]
		periods_ids = tuple(period_list[0][2])
		if based_on == 'payments':
			self.cr.execute('SELECT SUM(line.tax_amount) AS tax_amount, \
						SUM(line.debit) AS debit, \
						SUM(line.credit) AS credit, \
						COUNT(*) AS count, \
						account.id AS account_id, \
						account.name AS name,  \
						account.code AS code \
					FROM account_move_line AS line, \
						account_account AS account, \
						account_move AS move \
						LEFT JOIN account_invoice invoice ON \
							(invoice.move_id = move.id) \
					WHERE line.state<>%s \
						AND line.tax_code_id = %s  \
						AND line.account_id = account.id \
						AND account.company_id = %s \
						AND move.id = line.move_id \
						AND line.period_id IN %s \
						AND ((invoice.state = %s) \
							OR (invoice.id IS NULL))  \
					GROUP BY account.id,account.name,account.code',
						('draft',tax_code_id,company_id,periods_ids,'paid'))

		else :
			self.cr.execute('SELECT SUM(line.tax_amount) AS tax_amount, \
						SUM(line.debit) AS debit, \
						SUM(line.credit) AS credit, \
						COUNT(*) AS count, \
						account.id AS account_id, \
						account.name AS name,  \
						account.code AS code \
					FROM account_move_line AS line, \
						account_account AS account \
					WHERE line.state <> %s \
						AND line.tax_code_id = %s  \
						AND line.account_id = account.id \
						AND account.company_id = %s \
						AND line.period_id IN %s \
						AND account.active \
					GROUP BY account.id,account.name,account.code',
						('draft',tax_code_id,company_id,periods_ids))
		res = self.cr.dictfetchall()
		
						#AND line.period_id IN ('+ period_sql_list +') \
		
		i = 0
		while i<len(res):
			res[i]['account'] = self.pool.get('account.account').browse(self.cr, self.uid, res[i]['account_id'])
			i+=1
		return res

	def _get_codes(self,based_on, company_id, parent=False, level=0,period_list=[]):
		tc = self.pool.get('account.tax.code')
		ids = tc.search(self.cr, self.uid, [('parent_id','=',parent),('company_id','=',company_id)])
	
		res = []
		for code in tc.browse(self.cr, self.uid, ids, {'based_on': based_on}):
			res.append(('.'*2*level,code))
			
			res += self._get_codes(based_on, company_id, code.id, level+1)
		return res
	
	def _add_codes(self,based_on, account_list=[],period_list=[]):
		res = []
		for account in account_list:
			tc = self.pool.get('account.tax.code')
			ids = tc.search(self.cr, self.uid, [('id','=',account[1].id)])
			sum_tax_add = 0
			for period_ind in period_list[0][2]:
				for code in tc.browse(self.cr, self.uid, ids, {'period_id':period_ind,'based_on': based_on}):
					sum_tax_add = sum_tax_add + code.sum_period
					
			code.sum_period = sum_tax_add
			
			res.append((account[0],code))
		return res

	
	def _get_company(self, form):
		return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).name

	def _get_currency(self, form):
		return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).currency_id.name
	
	def sort_result(self,accounts):
		# On boucle sur notre rapport
		result_accounts = []
		ind=0
		old_level=0
		while ind<len(accounts):
			#
			account_elem = accounts[ind]
			#
			
			#
			# we will now check if the level is lower than the previous level, in this case we will make a subtotal
			if (account_elem['level'] < old_level):
				bcl_current_level = old_level
				bcl_rup_ind = ind - 1
				
				while (bcl_current_level >= int(accounts[bcl_rup_ind]['level']) and bcl_rup_ind >= 0 ):
					tot_elem = copy.copy(accounts[bcl_rup_ind])
					res_tot = { 'code' : accounts[bcl_rup_ind]['code'],
						'name' : '',
						'debit' : 0,
						'credit' : 0,
						'tax_amount' : accounts[bcl_rup_ind]['tax_amount'],
						'type' : accounts[bcl_rup_ind]['type'],
						'level' : 0,
						'pos' : 0
					}
					
					if res_tot['type'] == 1:
						# on change le type pour afficher le total
						res_tot['type'] = 2
						result_accounts.append(res_tot)
					bcl_current_level =  accounts[bcl_rup_ind]['level']
					bcl_rup_ind -= 1
					
			old_level = account_elem['level']
			result_accounts.append(account_elem)
			ind+=1
			
				
		return result_accounts
	

report_sxw.report_sxw('report.account.vat.declaration', 'account.tax.code',
	'addons/account/report/tax_report.rml', parser=tax_report, header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
