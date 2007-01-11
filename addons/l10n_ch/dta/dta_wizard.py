##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
import pooler
import wizard
from base64 import b64encode
from osv import osv
import time
import pooler
import mx.DateTime
from mx.DateTime import RelativeDateTime, DateTime

def _bank_get(self, cr, uid, context={}):
	pool = pooler.get_pool(cr.dbname)
	partner_id = pool.get('res.users').browse(cr,uid,[uid])[0].company_id.partner_id

	obj = pool.get('res.partner.bank')
	ids = obj.search(cr, uid, [('partner_id','=',partner_id.id)])
	res = obj.read(cr, uid, ids, ['active', 'name'], context)
	res = [(r['active'], r['name']) for r in res]
	return res 


check_form = """<?xml version="1.0"?>
<form string="DTA file creation">
<separator colspan="4" string="DTA Details :" />
	<field name="bank"/>
	<field name="journal"/>
	<field name="dta_line_ids" nolabel="1"  colspan="4" />
</form>
"""

check_fields = {
	'dta_line_ids' : {
		'string':'DTA lines',
		'type':'one2many',
		'relation':'account.dta.line',
		},
	'bank' : {
		'string':'Bank Account',
		'type':'selection',
		'selection':_bank_get,
		'required': True,
	},

	'journal' : {
		'string':'Journal',
		'type':'many2one',
		'relation':'account.journal',
		'domain':"[('type','=','cash')]",
		'required': True,
		'help':'The journal used for the bank statement',
	},
}


res_form = """<?xml version="1.0"?>
<form string="DTA file creation - Results">
<separator colspan="4" string="Clic on 'Save as' to save the DTA file :" />
	<field name="dta"/>
	<separator string="Logs" colspan="4"/>
	<field name="note" colspan="4" nolabel="1"/>
</form>
"""

res_fields = {
	'dta' : {
		'string':'DTA File',
		'type':'binary',
		'required':True,
		'readonly':True,
	},
	'note' : {'string':'Log','type':'text'}
}


def _get_bank(self,cr,uid,data,context):
	pool = pooler.get_pool(cr.dbname)
	user = pool.get('res.users').browse(cr,uid,[uid])[0]
	company= user.company_id
	
	if company.partner_id.bank_ids:
		bank = company.partner_id.bank_ids[0]
		return {'bank':bank.bank_name,'bank_code':bank.bank_code or ''} # 'city':'',

	return {}


def _get_dta_lines(self,cr,uid,data,context):
	pool = pooler.get_pool(cr.dbname)

	res= {}

	user = pool.get('res.users').browse(cr,uid,[uid])[0]
	company= user.company_id
	
	if company.partner_id.bank_ids:
		bank = company.partner_id.bank_ids[0]
		res.update({'bank':bank.bank_name,'bank_code':bank.bank_code or ''}) # 'city':'',


	dta_line_obj = pool.get('account.dta.line')
	lines=[]

	id_dta= pool.get('account.dta').create(cr,uid,{
		'date':time.strftime('%Y-%m-%d'),
		'user_id':uid,
		})


	for i in pool.get('account.invoice').browse(cr,uid,data['ids']):
		if i.dta_state in ['none','paid'] or i.state in ['draft','cancel','paid']:
			continue

		cash_disc_date=""
		discount=""
		if i.payment_term :
			disc_list= pool.get('account.payment.term').get_discounts(cr,uid,i.payment_term.id, i.date_invoice)

			for (cash_disc_date,discount) in disc_list:
				if cash_disc_date >= time.strftime('%Y-%m-%d'):
					break

		
		lines.append(dta_line_obj.create(cr,uid,{
			'name': i.id,
			'partner_id': i.partner_id.id,
			'due_date': i.date_due,
			'invoice_date': i.date_invoice,
			'cashdisc_date': cash_disc_date and cash_disc_date or None,
			'amount_to_pay': discount and i.amount_total*(1-discount) or i.amount_total,
			'amount_invoice': i.amount_total,
			'amount_cashdisc': discount and i.amount_total*(1-discount),
			'dta_id': id_dta,
			}))
		
	res.update({'dta_line_ids': lines,'dta_id': id_dta})
	return res



class record:
	def __init__(self,global_context_dict):
		self.fields = []
		self.global_values = global_context_dict
		self.pre={'padding':'','seg_num1':'01','seg_num2':'02',
						   'seg_num3':'03','seg_num4':'04','seg_num5':'05',
						   'type_paiement':'0', 'flag':'0', 'zero5':'00000'
						   }
		self.post={}
		self.init_local_context()

	def init_local_context(self):
		"""
		Must instanciate a fields list, field = (name,size)
		and update a local_values dict.
		"""
		raise "not implemented"

	def generate(self):
		res=''
		for field in self.fields :
			if self.pre.has_key(field[0]):
				value = self.pre[field[0]]
			elif self.global_values.has_key(field[0]):
				value = self.global_values[field[0]]
			elif self.post.has_key(field[0]):
				value = self.post[field[0]]
			else :
				print "ERROR field not found >>", field[0]
				#raise Exception(field[0]+' not found !')

			try:
				res = res + c_ljust(value, field[1])
			except :
				print "ERROR ljust >>",field[0], value , field[1]
			
		return res

class record_gt826(record):
	# -> bvr
	def init_local_context(self):
		print "gt826"
		self.fields=[
			('seg_num1',2),
			#header
			('date_value',6),('partner_bank_clearing',12),('zero5',5),('creation_date',6),
			('comp_bank_clearing',7), ('uid',5), 
			('sequence',5),
			('genre_trans',3),
			('type_paiement',1),('flag',1),
			#seg1
			('comp_dta',5),('invoice_number',11),('comp_bank_number',24),('date_value',6),
			('invoice_currency',3),('amount_to_pay',12),('padding',14),
			#seg2
			('seg_num2',2),('comp_name',20),('comp_street',20),('comp_zip',10),
			('comp_city',10),('comp_country',20),('padding',46),
			#seg3
			('seg_num3',2),('partner_bvr',12),#numero d'adherent bvr
			('padding',80),('invoice_reference',27),#communication structuree
			('padding',2)]

		self.pre.update({'partner_bank_clearing':'','partner_cpt_benef':'',
						 'type_paiement':'1', 'genre_trans':'826',
						 'conv_cours':'', 'option_id_bank':'D',
						 'ref2':'','ref3':'', 
						 'format':'0'})


class record_gt836(record):
	# -> iban
	def init_local_context(self):
		print "gt836"
		self.fields=[
			('seg_num1',2),
			#header
			('date_value',6),('partner_bank_clearing',12),('zero5',5),('creation_date',6),
			('comp_bank_clearing',7), ('uid',5), 
			('sequence',5),
			('genre_trans',3),
			('type_paiement',1),('flag',1),
			#seg1
			('comp_dta',5),('invoice_number',11),('comp_bank_number',24),('date_value',6),
			('invoice_currency',3),('amount_to_pay',15),('padding',11),
			#seg2
			('seg_num2',2),('conv_cours',12),('comp_name',35),('comp_street',35),('comp_zip',10),
			('comp_city',15),('comp_country',10),('padding',9),
			#seg3
			('seg_num3',2),('option_id_bank',1),('partner_bank_name',35),('partner_bank_city',35),
			('partner_iban',34),('padding',21),
			#seg4	
			('seg_num4',2),('partner_name',35),('partner_street',35),('partner_zip',10),('partner_city',15),
			('partner_country',10),('padding',21),
			#seg5										
			('seg_num5',2),('option_motif',1),('ref1',35),('ref2',35),('ref3',35),('format',1)]

		self.pre.update({'partner_bank_clearing':'','partner_cpt_benef':'',
						 'type_paiement':'1', 'genre_trans':'836',
						 'conv_cours':'', 'option_id_bank':'D',
						 'ref1': self.global_values['invoice_reference'],
						 'ref2':'','ref3':'', 
						 'partner_iban': self.global_values['partner_bank_number'],
						 'format':'0'})
		self.post.update({'option_motif':'U'})

class record_gt890(record):
	# -> total
	def init_local_context(self):
		print "gt890"
		self.fields=[
			('seg_num1',2),
			#header
			('date_value',6),('partner_bank_clearing',12),('zero5',5),('creation_date',6),
			('comp_bank_clearing',7), ('uid',5), 
			('sequence',5),
			('genre_trans',3),
			('type_paiement',1),('flag',1),
			#total
			('amount_total',16)]

		self.pre.update({'partner_bank_clearing':'','partner_cpt_benef':'',
							  'company_bank_clearing':'','genre_trans':'890'})
			
def c_ljust(s, size):
	"""
	check before calling ljust
	"""
	s= s or ''
	if len(s) > size:
		raise Exception("Too long data ! %s exceed %d character." % (s, size))
	return s.decode('utf-8').encode('latin1','replace').ljust(size)



def _create_dta(self,cr,uid,data,context):

	# cree des gt836
	v={}
	v['uid'] = str(uid)
	v['creation_date']= time.strftime('%y%m%d')
	log=''
	dta=''

	record_table = {'gt826':record_gt826,'gt836':record_gt836}
	
	pool = pooler.get_pool(cr.dbname)
	bank= pool.get('res.partner.bank').browse(cr,uid,[data['form']['bank']])[0]

	if not bank:
 		return {'note':'No bank account for the company.'}
	

 	v['comp_bank_name']= bank.name or False
 	v['comp_bank_clearing'] = bank.bank_code or False # clearing or swift

 	if not v['comp_bank_name'] and v['comp_bank_iban'] :
 		return {'note':'Bank account of the company not well defined.'}
	
	user = pool.get('res.users').browse(cr,uid,[uid])[0]
	company= user.company_id
	co_addr= company.partner_id.address[0]
	v['comp_country'] = co_addr.country_id and co_addr.country_id.name or ''
	v['comp_street'] = co_addr.street or ''
	v['comp_zip'] = co_addr.zip
	v['comp_city'] = co_addr.city
	v['comp_name'] = co_addr.name
	
	v['comp_dta'] = company.dta_number or ''
	if not company.dta_number :
		return {'note':'No dta number for the company.' }


	v['comp_bank_number'] = bank.number or ''

	if not v['comp_bank_number'] : # ex iban
		return {'note':'No account number for the company bank account.'}
	
	inv_obj = pool.get('account.invoice')
	dta_line_obj = pool.get('account.dta.line')

	seq= 1
	amount_tot = 0
	th_amount_tot= 0
	dta_id=data['form']['dta_id']

	if not dta_id :
		return {'note':'No dta line'}

	# write the bank account for the dta object
	pool.get('account.dta').write(cr,uid,[dta_id],{'bank':data['form']['bank']})

	dta_line_ids= []

	for line in data['form']['dta_line_ids']:
		if  line[1]!=0 and line[2] and line[2]['partner_id']:
			dta_line_ids.append(line[1])
			th_amount_tot += line[2]['amount_to_pay']
			dta_line_obj.write(cr, uid, [line[1]] , line[2] )


	# creation of a bank statement : TODO ajouter le partner 
 	bk_st_id = pool.get('account.bank.statement').create(cr,uid,{
 		'journal_id':data['form']['journal'],
 		'balance_start':0,
 		'balance_end_real':0, 
 		'state':'draft',
 		})

	for dtal in dta_line_obj.browse(cr,uid,dta_line_ids):
		i = dtal.name #dta_line.name = invoice's id
		invoice_number = i.number or '??'
		if not i.partner_bank_id:
			log= log +'\nNo partner bank defined. (invoice '+ invoice_number +')' 
			continue
		
		if i.dta_state in ['bv','bvr']:
			v['option_motif']= {'bv':'U','bvr':'I'}
		
		
		v['sequence'] = str(seq).rjust(5,'0')
		v['amount_to_pay']= str(dtal.amount_to_pay)
		v['invoice_number'] = invoice_number
		v['invoice_currency'] = i.currency_id.code or ''

		v['partner_bank_name'] =  i.partner_bank_id.bank_name or False
		v['partner_bank_clearing'] =  i.partner_bank_id.bank_code or False
		if not v['partner_bank_name'] and v['partner_bank_clearing']:
			log= log +'\nPartner bank account not well defined. (invoice '+ invoice_number +')' 
			continue

		v['partner_bank_number']=  i.partner_bank_id.number or False
		if not v['partner_bank_number']:
			log= log +'\nNo account number for the partner bank. (invoice '+ invoice_number +')' 
			continue

		v['partner_bvr']= i.partner_id.bvr_number or ''

		v['partner_bank_city']= 'FIXME'
		v['invoice_reference']= i.reference
		
		v['partner_name'] = i.partner_id and i.partner_id.name or ''
		if i.partner_id and i.partner_id.address and i.partner_id.address[0]:
			v['partner_street'] = i.partner_id.address[0].street
			v['partner_city']= i.partner_id.address[0].city
			v['partner_zip']= i.partner_id.address[0].zip
			v['partner_country']= i.partner_id.address[0].country_id.name
		else:
			v['partner_street'] =''
			v['partner_city']= ''
			v['partner_zip']= ''
			v['partner_country']= ''
			log= log +'\nNo address for the invoice partner. (invoice '+ invoice_number+')' 
		


		
		date_value = dtal.cashdisc_date or dtal.due_date
		if date_value :
			date_value = mx.DateTime.strptime( date_value,'%Y-%m-%d') or  mx.DateTime.now()
			v['date_value'] = date_value.strftime("%y%m%d")
		else:
			v['date_value'] = "000000"


		elec_pay = i.partner_bank_id.type_id.elec_pay
		if not elec_pay:
			log= log +'\nNo payment mode defined for the partner bank. (invoice '+ invoice_number +')' 
			continue
		if not record_table.has_key( elec_pay ):
			log= log +'\nPayment mode '+str(elec_pay)+' not supported. (invoice '+ invoice_number +')' 
			continue

		try:
			dta_line = record_table[ elec_pay ](v).generate()
		except Exception,e :
			log= log +'\nERROR:'+ str(e)+'(invoice '+ invoice_number+')' 
			dta_line_obj.write(cr,uid,[dtal.id],{'state':'cancel'})			
			raise
			continue

		#logging
		log = log + "Invoice : %s, Amount paid : %d %s, Value date : %s, State : Paid."%\
			  (invoice_number,dtal.amount_to_pay,v['invoice_currency'],date_value and date_value.strftime("%Y-%m-%d") or 'Empty date')


		pool.get('account.bank.statement.line').create(cr,uid,{
			'name':i.number,
			'date':date_value,
			'amount':dtal.amount_to_pay,
			'type':{'out_invoice':'customer','in_invoice':'supplier','out_refund':'customer','in_refund':'supplier'}[i.type],
			'partner_id':i.partner_id.id,
			'account_id':i.account_id.id,
			'statement_id': bk_st_id,
			'invoice_id': i.id,
			})

		dta = dta + dta_line
		amount_tot += dtal.amount_to_pay
		inv_obj.write(cr,uid,[i.id],{'dta_state':'paid'})
		dta_line_obj.write(cr,uid,[dtal.id],{'state':'done'})
		seq += 1
	
		
	# bank statement updated with the total amount :
	pool.get('account.bank.statement').write(cr,uid,[bk_st_id],{'balance_end_real': amount_tot})
	
	# segment total 
	v['amount_total'] = str(amount_tot)
	try:
		if dta :
			dta = dta + record_gt890(v).generate()
	except Exception,e :
		log= log +'\n'+ str(e) + 'CORRUPTED FILE !\n'
		raise
		

	log = log + "\n--\nSummary :\nTotal amount paid : %.2f\nTotal amount expected : %.2f"%(amount_tot,th_amount_tot) 
	pool.get('account.dta').write(cr,uid,[dta_id],{'note':log,'name':b64encode(dta or "")})
	
	return {'note':log, 'dta': b64encode(dta)}



class wizard_dta_create(wizard.interface):
	states = {
		
		'init':{
		'actions' : [_get_dta_lines],
		'result' : {'type' : 'form',
				    'arch' : check_form,
				    'fields' : check_fields,
				    'state' : [('end', 'Cancel'),('creation', 'Yes') ]}
		},

		'creation' : {
			'actions' : [_create_dta],
			'result' : {'type' : 'form',
						'arch' : res_form,
						'fields' : res_fields,
						'state' : [('end', 'Quit') ]}
		},

	}

wizard_dta_create('account.dta_create')
