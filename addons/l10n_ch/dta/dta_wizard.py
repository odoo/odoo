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
		return {'bank':bank.bank_name,'bank_iban':bank.iban or ''} # 'city':'',

	return {}

# def _cleaning(self,cr,uid,data,context):
# 	pool = pooler.get_pool(cr.dbname)
# 	print [ line[1] for line in data['form']['dta_line_ids']]
# 	pool.get('account.dta').unlink(cr, uid, [ line[1] for line in data['form']['dta_line_ids'] ])
# 	return {}


def _get_dta_lines(self,cr,uid,data,context):
	pool = pooler.get_pool(cr.dbname)

	res= {}

	user = pool.get('res.users').browse(cr,uid,[uid])[0]
	company= user.company_id
	
	if company.partner_id.bank_ids:
		bank = company.partner_id.bank_ids[0]
		res.update({'bank':bank.bank_name,'bank_iban':bank.iban or ''}) # 'city':'',


	dta_line_obj = pool.get('account.dta.line')
	lines=[]

	id_dta= pool.get('account.dta').create(cr,uid,{
		'date':time.strftime('%Y-%m-%d'),
		'user_id':uid,
		})


	for i in pool.get('account.invoice').browse(cr,uid,data['ids']):
		if i.dta_state != '2bpaid' or i.state in ['draft','cancel','paid']:
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

def c_ljust(s, size):
	"""
	check before calling ljust
	"""
	s= s or ''
	if len(s) > size:
		raise Exception("Too long data ! %s exceed %d character." % (s, size))
	return s.decode('utf-8').encode('latin1','replace').ljust(size)


def segment_01(header,iddta,inv_num,iban,value,currency,amount):
	return '01'+c_ljust(header,51)+c_ljust(iddta,5)+c_ljust(inv_num,11)+c_ljust(iban,24)+c_ljust(value,6)\
		   +c_ljust(currency,3)+c_ljust(amount,15)+''.ljust(11)

def segment_02(name,street,zip,city,country,cours='', num_seg='02'):
	zip = zip or ''
	country = country or ''
	city = city or ''
	add = ' '.join([zip,city,country])
	return c_ljust(cours,12)+c_ljust(name,35)+c_ljust(street,35)+ c_ljust(add,35)+''.ljust(9)

def segment_03(bank_name,bank_city,iban):
	return "03"+"D"+c_ljust(bank_name,35)+c_ljust(bank_city,35)+c_ljust(iban,34)+''.ljust(21)

def segment_04(name,street,zip,city,country,cours='', num_seg='04'):
	return segment_02(name,street,zip,city,country,cours, num_seg)

def segment_05(motif='I',ref1='',ref2='',ref3='',format='0'):
	return '05'+c_ljust(ref1,35)+c_ljust(ref2,35)+c_ljust(ref3,35)+c_ljust(format,1)+''.ljust(19)

def header(date,cpt_benef,creation_date,cpt_donneur,id_fich,num_seq,trans,type):
	return c_ljust(date,6)+c_ljust(cpt_benef,12)+c_ljust('00000',5)+c_ljust(creation_date,6)+c_ljust(cpt_donneur,7)\
		   +c_ljust(id_fich,5)+ str(num_seq).rjust(5,'0')+ c_ljust(trans,3) + c_ljust(type,1)+'0'

def total(header,tot):
	return '01'+c_ljust(header,51)+c_ljust(tot,16)+''.ljust(59)

def _create_dta(self,cr,uid,data,context):

	# pour generaliser (plus) facilement : utiliser un design patern
	# transaction :
	# def trans(methode)
	#    def capsule(a,*a,**a)
	#        try methode
	#        except ...
	#    return capsule
	# on peut ensuite l'utiliser via @trans
	# devant la methode concernee
	
	# cree des gt836

	creation_date= time.strftime('%y%m%d')
	log=''
	dta=''
	pool = pooler.get_pool(cr.dbname)
	bank= pool.get('res.partner.bank').browse(cr,uid,[data['form']['bank']])[0]
	bank_name= bank.name or ''
	bank_iban = bank.iban or ''
	if not bank_name and bank_iban :
		return {'note':'Bank account not well defined.'}
	
	user = pool.get('res.users').browse(cr,uid,[uid])[0]
	company= user.company_id
	co_addr= company.partner_id.address[0]

	company_dta = company.dta_number or ''
	if not company.dta_number :
		return {'note':'No dta number for the company.' }

	company_iban = company.partner_id and company.partner_id.bank_ids and company.partner_id.bank_ids[0]\
				   and company.partner_id.bank_ids[0].iban or ''
	if not company_iban :
		return {'note':'No iban number for the company.'}
	
	inv_obj = pool.get('account.invoice')
	dta_line_obj = pool.get('account.dta.line')
	seq= 1
	amount_tot= 0
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


		number = i.number or ''
		currency = i.currency_id.code or ''
		country = co_addr.country_id and co_addr.country_id.name or ''

		partner_bank_account = i.partner_id and i.partner_id.bank_ids and i.partner_id.bank_ids[0]\
							   and i.partner_id.bank_ids[0].iban or ''

		partner_name = i.partner_id and i.partner_id.name or ''
		if i.partner_id and i.partner_id.address and i.partner_id.address[0]:
			partner_street = i.partner_id.address[0].street
			partner_city= i.partner_id.address[0].city
			partner_zip= i.partner_id.address[0].zip
			partner_country= i.partner_id.address[0].country_id.name

		else:
			partner_street =''
			partner_city= ''
			partner_zip= ''
			partner_country= ''
			log= log +'\nNo address for the invoice partner. (invoice '+ (i.number or '??')+')' 
		
		if not partner_bank_account:
			log= log +'\nNo bank account for the invoice partner. (invoice '+ (i.number or '??')+')' 
			continue


		
		date_value = dtal.cashdisc_date or dtal.due_date or ""
		date_value = date_value and mx.DateTime.strptime( date_value,'%Y-%m-%d') or  mx.DateTime.now()
		

		try:
			#header
			hdr= header('000000','',creation_date,company_iban,'idfi',seq,'836','0') # TODO id_file
			
			dta_line = ''.join([segment_01(hdr,company_dta,# segment 01:
								   number,company_iban,date_value.strftime("%y%m%d")
											 ,currency,str(dtal.amount_to_pay)),							   # adresse donneur d'ordre
							   segment_02(company.name,co_addr.street,co_addr.zip,co_addr.city,country,cours=''),# donnees de la banque
							   segment_03(bank_name,'',bank_iban),# adresse du beneficiaire							   
							   segment_04(partner_name,partner_street,partner_zip,partner_city,partner_country,cours=''),# communication
								                                                                                   #& reglement des frais							   
							   segment_05(motif='I',ref1='',ref2=i.reference or '',ref3='',format='0') ])#FIXME : motif

		except Exception,e :
			log= log +'\nERROR:'+ str(e)+'(invoice '+ (i.number or '??')+')' 
			dta_line_obj.write(cr,uid,[dtal.id],{'state':'cancel'})			
			#raise
			continue

		#logging
		log = log + "Invoice : %s, Amount paid : %d %s, Value date : %s, State : Paid."%\
			  (i.number,dtal.amount_to_pay,currency,date_value.strftime('%Y-%m-%d'))


		pool.get('account.bank.statement.line').create(cr,uid,{
			'name':i.number,
			'date':date_value.strftime('%Y-%m-%d'), 
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
	try:
		if dta :
			dta = dta + total(header('000000','',creation_date,company_iban,str(uid),seq,'890','0')\
						  , str(amount_tot))
	except Exception,e :
		log= log +'\n'+ str(e) + 'CORRUPTED FILE !\n'
		#raise
		

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
