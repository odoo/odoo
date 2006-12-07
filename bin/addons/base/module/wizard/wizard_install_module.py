# -*- coding: iso-8859-1 -*-
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

import wizard
import netsvc

#TODO: upgraded modules
#TODO: removed modules
additional_changes_form = '''<?xml version="1.0"?>
<form string="Additional modules">
	<label string="The following additional modules need to be installed:"/>
	<newline/>
	<field name="additional"/>
</form>'''

additional_changes_fields = {
	'additional': {'string':'Additional modules', 'type':'one2many', 'relation':'ir.module.module', 'readonly':True},
}

class wizard_install_module(wizard.interface):
	def _get_value(self, cr, uid, data, context):
		service = netsvc.LocalService("object_proxy")
		extra = service.execute(cr.dbname, uid, 'ir.module.module', 'get_extra_modules', data['ids'])
		return {'additional': extra}

	def _install_module(self, cr, uid, data, context):
		service = netsvc.LocalService("object_proxy")
		res = service.execute(cr.dbname, uid, 'ir.module.module', 'install', data['ids'])
		return {}

	states = {
		'init': {
			'actions': [_get_value], 
			'result': {'type':'form', 'arch':additional_changes_form, 'fields':additional_changes_fields, 'state':[('install','Install'), ('end','Cancel')]}
		},
		'install': {
			'actions': [_install_module],
			'result': {'type':'state', 'state':'end'}
		},
	}
wizard_install_module('module.module.install')

