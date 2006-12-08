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
from osv.osv import  except_osv 
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

	# TODO:
	# - verifier que la ligne de somme coincide avec le reste
	# - verifier que chaque est au bon format : que des num,
	#   bin nbre de num, ... ex: "123".isdigit()
	# Attention : p-e dependant de la banque ...
	
	# TODO (trunk) :
	
	pool = pooler.get_pool(cr.dbname)
	v11 = pool.get('account.v11').browse(cr, uid, data['ids'])[0]

	line=""
	record={}
	total={}
	total_compute= 0
	rec_list=[]

	for char  in b64decode(v11.file):

		if not char == '\n':
			line += char

		else :
			
			record['genre'] = line[0:3]

			print line
			print line[0:]
			print record['genre']
			print 
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
				}
				
				total_compute+= int(record['montant'])
				rec_list.append( record )

			line=""

			#for key in sorted(record.keys()):
			#print key," : ", record[key]


	# TODO : raise a correct error message
	if not total_compute == int(total['tot_montant']):
		raise except_osv('warning', 'Incoherent v11 file !')
	else:

		period_id = pool.get('account.period').find(cr,uid, context=context)
		if not period_id:
			raise osv.except_osv('No period found !', 'Unable to find a valid period !')
		period_id = period_id[0]
		invoice_obj= pool.browse('account.invoice')
		for rec in rec_list:

			move_id = pool.get('account.move').create(cr, uid, {
 				'name': 'Imported from v11',
				'period_id': period_id,
				'journal_id': data['form']['journal_id']
			})

			invoice_id= invoice_obj.search(cr,uid,[ ('number','=',rec['internal_ref']) ])
			invoice = invoice_obj.browse(cr, uid, invoice_id)
			acc1 = invoice.partner_id.property_account_receivable
			acc2 = journal.default_debit_account_id
			
			#
			# Vérifier que tu recois bien un int, sinon [0]
			#

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
		

	#print total
	#print rec_list


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



