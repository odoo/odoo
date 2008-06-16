##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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
import osv
import pooler
import os
import tools

import zipfile
import StringIO
import base64

finish_form ='''<?xml version="1.0"?>
<form string="Module import">
	<label string="Module successfully imported !" colspan="4"/>
</form>
'''

ask_form ='''<?xml version="1.0"?>
<form string="Module import">
	<separator string="Module import" colspan="4"/>
	<label string="Please give your module .ZIP file to import." colspan="4"/>
	<field name="module_file"/>
</form>
'''

ask_fields = {
	'module_file': {'string': 'Module .ZIP file', 'type': 'binary', 'required': True},
}

class move_module_wizard(wizard.interface):
	def importzip(self, cr, uid, data, context):
		module_obj=pooler.get_pool(cr.dbname).get('ir.module.module')
		module_data = data['form']['module_file']

		val =base64.decodestring(module_data)
		fp = StringIO.StringIO(val)
		fdata = zipfile.ZipFile(fp, 'r')
		fname = fdata.namelist()[0]
		module_name = os.path.split(fname)[0]

		ad = tools.config['addons_path']

		fname = os.path.join(ad,module_name+'.zip')
		try:
			fp = file(fname, 'wb')
			fp.write(val)
			fp.close()
		except IOError, e:
			raise wizard.except_wizard('Error !', 'Can not create the module file:\n'+'  '+fname+'!')

		pooler.get_pool(cr.dbname).get('ir.module.module').update_list(cr, uid)
		return {'module_name': module_name}

	def _action_module_open(self, cr, uid, data, context):
		return {
			'domain': str([('name', '=', data['form']['module_name'])]),
			'name': 'Module List',
			'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'ir.module.module',
			'view_id': False,
			'type': 'ir.actions.act_window'
		}

	states = {
		'init': {
			'actions': [],
			'result': {
				'type': 'form',
				'arch': ask_form,
				'fields': ask_fields,
				'state': [
					('end', 'Cancel', 'gtk-cancel'),
					('import', 'Import module', 'gtk-ok', True)
				]
			}
		},
		'import': {
			'actions': [importzip],
			'result': {
				'type':'form',
				'arch':finish_form,
				'fields':{},
				'state':[('open_window','Close')]
			}
		},
		'open_window': {
			'actions': [],
			'result': {'type': 'action', 'action': _action_module_open, 'state':'end'}
		},
	}
move_module_wizard('base.module.import')
