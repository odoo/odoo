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
import time
import wizard
import netsvc
from base64 import b64decode
from osv import osv

ask_form = """<?xml version="1.0"?>
<form string="V11 parsing">
<separator colspan="4" string="Extract V11 data :" />
	<field name="journal_id" colspan="1"/>
	<newline/>
	<field name="v11"/>
</form>
"""

ask_fields = {
	'journal_id' : {
		'string':'Destination Journal',
		'type':'many2one',
		'relation':'account.journal',
		'required':True,
	},
	'v11' : {
		'string':'V11 file',
		'type':'binary',
		'required':True,
	},

}

res_form = """<?xml version="1.0"?>
<form string="V11 parsing">
<separator colspan="4" string="Results :" />
	<field name="journal_id"/>
	<newline/>
	<field name="v11"/>
	<separator string="Logs" colspan="4"/>
	<field name="note" colspan="4" nolabel="1"/>
</form>
"""

res_fields = {
	'journal_id' : {
		'string':'Destination Journal',
		'type':'many2one',
		'relation':'account.journal',
		'required':True,
	},
	'v11' : {
		'string':'V11 file',
		'type':'binary',
		'required':True,
	},

	'note' : {'string':'Log','type':'text'}

}



def _v11_parsing(self, cr, uid, data, context):

	pool = pooler.get_pool(cr.dbname)
	v11 = data['form']['v11']
	

	line=""
	record={}
	total={}
	total_compute= 0
	rec_list=[]
	log=''
	nb_err=0

	# v11 parsing :
	for char  in b64decode(v11):

		if not char == '\n':
			line += char

		else :

			record['genre'] = line[0:3]

			if record['genre'] == '999':



				total={'n_postal': line[3:12],
				  'cle': line[12:39],
				  'tot_montant': line[39:51],
				  'nb_rec': line[51:63],
				  'date_etabl': line[63:69],
				  'tot_frais_encaissement': line[69:78],
				}

			else :

				record={'n_postal': line[3:12],
						'n_ref': line[12:39],
						'montant': line[39:49],
						'reserve': line[49:59],
						'date_remise': line[59:65],
						'date_comptable': line[65:71],
						'date_valeur': line[71:77],
						'invoice_ref': line[77:87],
						'reserve2': line[87:96],
						'frais_encaissement': line[96:100],
						'line':line,
				}

				total_compute+= int(record['montant'])
				rec_list.append( record )

			line=""


	# check the amounts :
	if not total_compute == int(total['tot_montant']):
		return {'note': 'Incoherent V11 file  ! IMPORT ABORTED.' }



	period_id = pool.get('account.period').find(cr,uid, context=context)
	if not period_id:
		return {'note': 'No period found  ! IMPORT ABORTED.' }

	period_id = period_id[0]
	invoice_obj= pool.get('account.invoice')

	acc2 = pool.get('account.journal').browse(cr,uid,data['form']['journal_id'],context).default_debit_account_id.id
	if not 	acc2:
		return {'note': 'No debit account specified for this journal ! IMPORT ABORTED.' }



	for rec in rec_list:

		# get the invoice via his number
		try:
			invoice_id= invoice_obj.search(cr,uid,[ ('number','=',int(rec['invoice_ref'])) ])[0]
		except:
			log = log + '\n * No invoice with invoice number '+ rec['invoice_ref'].lstrip('0') + '.\n  line : '+rec['line']
			nb_err+=1
			continue
		invoice = invoice_obj.browse(cr, uid, invoice_id)

		try:
			acc1 = invoice.partner_id.property_account_receivable[0]
		except:
			log = log + '\n * invoice with number '+ rec['invoice_ref'].lstrip('0') +' has no partner !'+ '\n  line : '+rec['line']
			nb_err+=1
			continue

		try:
			move_id = pool.get('account.move').create(cr, uid, {
				'name': 'Imported from v11',
				'period_id': period_id,
				'journal_id': data['form']['journal_id']
				})
			line_id = pool.get('account.move.line').create(cr,uid,{
				'name': 'v11', # maybe a better name ..
				'debit': 0,
				'credit': rec['montant'],
				'account_id': acc1,
				'move_id': move_id,
				'partner_id': invoice.partner_id.id,
				'date': time.strftime('%Y-%m-%d'),
				'period_id': period_id,
				'journal_id': data['form']['journal_id']

				})
			pool.get('account.move.line').create(cr,uid,{
				'name': 'v11',
				'debit': rec['montant'],
				'credit': 0,
				'account_id': acc2,
				'move_id': move_id,
				'partner_id': invoice.partner_id.id,
				'date': time.strftime('%Y-%m-%d'),
				'period_id': period_id,
				'journal_id': data['form']['journal_id']

				})
			account_move_lines = invoice.move_line_id_payment_get(cr,uid,[invoice.id])

			if not account_move_lines:
				raise Exception("No moves associated to invoice number "+ rec['invoice_ref'].lstrip('0'))
			account_move_lines.append(line_id )
			pool.get('account.move.line').reconcile(cr,uid,account_move_lines,
													writeoff_acc_id=0,
													writeoff_journal_id=0,
													writeoff_period_id= 0,
													)
			cr.commit()

		except osv.except_osv, e:
			cr.rollback() 
			nb_err+=1
			if e.value.startswith('You have to provide an account for the write off entry !'):
				log= log +'\n * Error amount mismatch for invoice '+ rec['invoice_ref'].lstrip('0')+\
					'( expected amount: '+str(invoice.amount_total)+' got :'+rec['montant'].lstrip('0')+\
					').\n  line : '+rec['line']
			else:
				log= log +'\n * '+str(e.value)+  ' :\n  line : '+rec['line']
			#raise # REMOVEME

		except Exception, e:
			cr.rollback()
			nb_err+=1
			log= log +'\n * '+str(e)+  ' :\n  line : '+rec['line'] 
			#raise # REMOVEME
		except :
			cr.rollback()
			nb_err+=1
			log= log +'\n * Reconciliation Error\n  line : '+rec['line'] 
			#raise

	log= log + '-'*5 +'\nNumber of parsed lines : '+ str(len(rec_list)) +'\nNumber of error : '+ str(nb_err)

	return {'note':log,'journal_id': data['form']['journal_id'], 'v11': data['form']['v11']}


# def _init(self, cr, uid, data, context):
# 	if not data['form']:
# 		return {}
# 	return {'journal_id': data['form']['journal_id'], 'v11': data['form']['v11']}

class v11_import(wizard.interface):
	states = {
		'init' : {
			'actions' : [],
			'result' : {'type' : 'form',
				    'arch' : ask_form,
				    'fields' : ask_fields,
				    'state' : [('end', 'Cancel'),('extraction', 'Yes') ]}
		},
		'extraction' : {
			'actions' : [_v11_parsing],
			'result' : {'type' : 'form',
						'arch' : res_form,
						'fields' : res_fields,
						'state' : [('extraction', 'Retry') ,('end', 'Quit') ]}
		},

	}
v11_import("account.v11_import")



