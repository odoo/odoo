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
import ir
import netsvc
from time import sleep
from base64 import b64decode


test_form = """<?xml version="1.0"?>
<form string="V11 parsing">
	<separator colspan="4" string="Extract V11 data ?" />
	<field name="journal_id"/>
</form>
"""

test_fields = {
	'journal_id' : {
		'string':'Destination Journal',
		'type':'many2one',
		'relation':'account.journal',
		'required':True,
#		'domain':[('type','=','sale')]
	},

}


def _v11_parsing(self, cr, uid, data, context):

	pool = pooler.get_pool(cr.dbname)
	v11_obj = pool.get('account.v11')
	
	for v11 in v11_obj.browse(cr, uid, data['ids']):

		line=""
		record={}
		total={}
		total_compute= 0
		rec_list=[]
		log=''


		# v11 parsing :
		for char  in b64decode(v11.file):

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
							'internal_ref': line[77:87],
							'reserve2': line[87:96],
							'frais_encaissement': line[96:100],
							'line':line,
					}

					total_compute+= int(record['montant'])
					rec_list.append( record )

				line=""


		# check the amounts :
		if not total_compute == int(total['tot_montant']):
			raise wizard.except_wizard('warning', 'Incoherent v11 file !')
			continue
		


		period_id = pool.get('account.period').find(cr,uid, context=context)
		if not period_id:
			raise wizard.except_wizard('No period found !', 'Unable to find a valid period !')
		period_id = period_id[0]
		invoice_obj= pool.get('account.invoice')
		for rec in rec_list:



			# recherche sur l'id (pr garder un num absolu):
			# implique de mettre l'id sur le bvr..
			invoice_id= invoice_obj.search(cr,uid,[ ('id','=',int(rec['internal_ref'])) ])[0]
			print invoice_id
			invoice = invoice_obj.browse(cr, uid, invoice_id)
			invoice_obj.write(cr,uid,[invoice_id],{'state':'paid'})



			# TODO feedbacker en log les erreurs
			acc2 = pool.get('account.journal').browse(cr,uid,data['form']['journal_id'],context).default_debit_account_id.id
			if not 	acc2:
				raise wizard.except_wizard('Warning !', 'No debit account specified for this journal !')
				continue

			# TODO idem
			try:
				acc1 = invoice.partner_id.property_account_receivable[0]
			except:
				raise wizard.except_wizard('Warning !','invoice with number '+str(int(rec['internal_ref'])) +' has no partner !')
				continue



			move_id = pool.get('account.move').create(cr, uid, {
				'name': 'Imported from v11',
				'period_id': period_id,
				'journal_id': data['form']['journal_id']
			})


			
			pool.get('account.move.line').create(cr,uid,{
				'name': 'v11',
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



		log= log + 'Number of parsed lines : '+ str(len(rec_list)) +'\nTotal amount for this bvr : '+ str(int(total['tot_montant']))+' '+invoice.currency_id.name


		v11.write(cr,uid,[v11.id],{'note': log })

		# peut-etre retourner un nouvel onglet avec la liste des ecritures generee :
	return {}




class v11_import(wizard.interface):
	states = {
		'init' : {
			'actions' : [],
			'result' : {'type' : 'form',
				    'arch' : test_form,
				    'fields' : test_fields,
				    'state' : [('end', 'Cancel'),('extraction', 'Yes') ]}
		},
		'extraction' : {
			'actions' : [_v11_parsing],
			'result' : {'type' : 'state', 'state' : 'end'}
		},

# 		'result' : {
# 			'actions' : [],
# 			'result' : {'type' : 'form',
# 						'state' : 'end'}
# 		},



	}
v11_import("account.v11_import")



