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

def _bank_get(self, cr, uid, context={}):
	pool = pooler.get_pool(cr.dbname)
	partner_id = pool.get('res.users').browse(cr,uid,[uid])[0].company_id.partner_id

	obj = pool.get('res.partner.bank')
	ids = obj.search(cr, uid, [('partner_id','=',partner_id.id)])
	res = obj.read(cr, uid, ids, ['active', 'name'], context)
	res = [(r['active'], r['name']) for r in res]
	return res 


ask_form = """<?xml version="1.0"?>
<form string="DTA file creation">
<separator colspan="4" string="Choose a bank account :" />
	<field name="bank" colspan="3"/>
</form>
"""

ask_fields = {
	'bank' : {
		'string':'Bank Account',
		'type':'selection',
		'selection':_bank_get,
		'required': True,
	},
}

check_form = """<?xml version="1.0"?>
<form string="DTA file creation">
<separator colspan="4" string="DTA Details :" />
	<field name="dta_line_ids" nolabel="1"  colspan="4" />
</form>
"""
check_fields = {
	'dta_line_ids' : {
		'string':'DTA lines',
		'type':'one2many',
		'relation':'account.dta.line',
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

def _cleaning(self,cr,uid,data,context):
	pool = pooler.get_pool(cr.dbname)
	pool.get('account.dta').unlink(cr, uid, [ line[1] for line in data['form']['dta_line_ids'] ])
	return {}


def _get_dta_lines(self,cr,uid,data,context):
	pool = pooler.get_pool(cr.dbname)
	dta_line_obj = pool.get('account.dta.line')
	lines=[]

	id_dta= pool.get('account.dta').create(cr,uid,{
		'bank':data['form']['bank'],
		'date':time.strftime('%Y-%m-%d'),
		'user_id':uid,
		})


	for i in pool.get('account.invoice').browse(cr,uid,data['ids']):
		if i.dta_state != '2bpaid' or i.state in ['draft','cancel','paid']:
			continue

		discount = i.payment_term and i.payment_term.cash_discount_ids and i.payment_term.cash_discount_ids[0] or False 
		if discount and time.strftime('%Y-%m-%d') <= discount.date :
			amount_to_pay = i.amount_total*(1-discount.discount)
		else :
			amount_to_pay = i.amount_total
			
		lines.append(dta_line_obj.create(cr,uid,{
			'name':i.id,
			'partner_id':i.partner_id.id,
			'due_date':i.date_due,
			'cashdisc_date': discount and discount.date,
			'amount_to_pay': amount_to_pay,
			'amount_invoice':i.amount_total,
			'amount_cashdisc': discount and i.amount_total*(1-discount.discount),
			'dta_id': id_dta,
			}))

	return {'dta_line_ids': lines,'dta_id': id_dta}

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
	err_log=''
	dta=''
	valeur=''
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

	count = 0 
	for line in data['form']['dta_line_ids']:
		if not line[1]:
			del data['form']['dta_line_ids'][count]
		else:
			dta_line_obj.write(cr, uid, [line[1]] , line[2] )
		count += 1
		th_amount_tot += line[2]['amount_to_pay']

	if not dta_id :
		return {'note':'No dta line'}

		
	for dtal in dta_line_obj.browse(cr,uid,[ line[1] for line in data['form']['dta_line_ids'] ]):

		dta_line = ""
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
			err_log= err_log +'\nNo address for the invoice partner. (invoice '+ (i.number or '??')+')' 
		
		if not partner_bank_account:
			err_log= err_log +'\nNo bank account for the invoice partner. (invoice '+ (i.number or '??')+')' 
			continue

		#header
		try:
			hdr= header('000000','',creation_date,company_iban,'idfi',seq,'836','0') # TODO id_file
		except Exception,e :
			err_log= err_log +'\n'+ str(e)+'(invoice '+ (i.number or '??')+')' 
			dtal_line_obj.write(cr,uid,[dtal.id],{'state':'cancel'})
			continue
		# segment 01:
		try:
			dta_line = dta_line + segment_01(hdr,company_dta ,
								   number,company_iban,valeur,currency,str(dtal.amount_to_pay))
		except Exception,e :
			err_log= err_log +'\n'+ str(e)+'(invoice '+ (i.number or '??')+')' 
			dtal_line_obj.write(cr,uid,[dtal.id],{'state':'cancel'})			
			continue
		# adresse donneur d'ordre
		try: 
			dta_line = dta_line + segment_02(company.name,co_addr.street,co_addr.zip,co_addr.city,country,cours='')
		except Exception,e :
			err_log= err_log +'\n'+ str(e)+'(invoice '+ (i.number or '??')+')' 
			dtal_line_obj.write(cr,uid,[dtal.id],{'state':'cancel'})			
			continue
		# donnees de la banque
		try: 
			dta_line = dta_line + segment_03(bank_name,'',bank_iban) 
		except Exception,e :
			err_log= err_log +'\n'+ str(e)+'(invoice '+ (i.number or '??')+')' 
			dtal_line_obj.write(cr,uid,[dtal.id],{'state':'cancel'})			
			continue
		# adresse du beneficiaire
		try: 
			dta_line = dta_line + segment_04(partner_name,partner_street,partner_zip,partner_city,partner_country,cours='')
		except Exception,e :
			err_log= err_log +'\n'+ str(e)+'(invoice '+ (i.number or '??')+')' 
			dtal_line_obj.write(cr,uid,[dtal.id],{'state':'cancel'})			
			continue
		# communication & reglement des frais
		try: 
			dta_line = dta_line + segment_05(motif='I',ref1='',ref2=i.reference or '',ref3='',format='0') #FIXME : motif
		except Exception,e :
			err_log= err_log +'\n'+ str(e)+'(invoice '+ (i.number or '??')+')' 
			dtal_line_obj.write(cr,uid,[dtal.id],{'state':'cancel'})			
			continue

		dta = dta + dta_line
		amount_tot += dtal.amount_to_pay
		inv_obj.write(cr,uid,[i.id],{'dta_state':'paid'})
		dta_line_obj.write(cr,uid,[dtal.id],{'state':'done'})
		seq += 1


	# total
	try:
		if dta :
			dta = dta + total(header('000000','',creation_date,company_iban,str(uid),seq,'890','0')\
						  , str(amount_tot))
	except Exception,e :
		err_log= err_log +'\n'+ str(e) + 'CORRUPTED FILE !\n'
		#raise
		

	err_log = err_log + "\nSummary :\nTotal amount paid : %.2f\nTotal amount expected : %.2f"%(amount_tot,th_amount_tot) 
	pool.get('account.dta').write(cr,uid,[dta_id],{'note':err_log,'name':b64encode(dta or "")})
	
	return {'note':err_log, 'dta': b64encode(dta)}



class wizard_dta_create(wizard.interface):
	states = {
		'init' : {
			'actions' : [_get_bank],
			'result' : {'type' : 'form',
				    'arch' : ask_form,
				    'fields' : ask_fields,
				    'state' : [('end', 'Cancel'),('check', 'Yes') ]}
		},
		
		'check':{
		'actions' : [_get_dta_lines],
		'result' : {'type' : 'form',
				    'arch' : check_form,
				    'fields' : check_fields,
				    'state' : [('clean', 'Cancel'),('creation', 'Yes') ]}
		},

		'clean':{
		'actions' : [_cleaning],
		'result' : {'type' : 'state',
				    'state' : 'end',}
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
