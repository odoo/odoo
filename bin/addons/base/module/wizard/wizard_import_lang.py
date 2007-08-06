# -*- coding: iso-8859-1 -*-
##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
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

import wizard
import tools
import base64
import pooler

view_form="""<?xml version="1.0"?>
<form string="Import language">
	<image name="gtk-dialog-info" colspan="2"/>
	<group colspan="2" col="4">
		<separator string="Import new language" colspan="4"/>
		<field name="name"/>
		<field name="code"/>
		<field name="data" colspan="3"/>
		<label string="You have to import a .CSV file wich is encoded in UTF-8.\nPlease check that the first line of your file is:" colspan="4" align="0.0"/>
		<label string="type,name,res_id,src,value" colspan="4"/>
	</group>
</form>"""

class wizard_import_lang(wizard.interface):
	def _import_lang(self, cr, uid, data, context):
		form=data['form']
		buf=base64.decodestring(data['form']['data']).split('\n')
		tools.trans_load_data(cr.dbname, buf, form['code'], lang_name=form['name'])
		return {}
	fields_form={
		'name':{'string':'Language name', 'type':'char', 'size':64, 'required':True},
		'code':{'string':'Code (eg:en_US)', 'type':'char', 'size':5, 'required':True},
		'data':{'string':'File', 'type':'binary', 'required':True},
	}
	states={
		'init':{
			'actions': [],
			'result': {'type': 'form', 'arch': view_form, 'fields': fields_form,
				'state':[
					('end', 'Cancel', 'gtk-cancel'),
					('finish', 'Ok', 'gtk-ok', True)
				]
			}
		},
		'finish':{
			'actions':[],
			'result':{'type':'action', 'action':_import_lang, 'state':'end'}
		},
	}
wizard_import_lang('module.lang.import')
